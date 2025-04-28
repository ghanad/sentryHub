# integrations/tasks.py

import logging
import json
import re
from typing import Optional, Dict, Any

from celery import shared_task, Task
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist

# Import models and service correctly
from integrations.models import JiraIntegrationRule
from alerts.models import AlertGroup, AlertInstance
from integrations.services.jira_service import JiraService


logger = logging.getLogger(__name__)

# Base task with retry logic
class JiraTaskBase(Task):
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3, 'countdown': 15}
    retry_backoff = True
    retry_jitter = True

@shared_task(bind=True, base=JiraTaskBase)
def process_jira_for_alert_group(self, alert_group_id: int, rule_id: int, alert_status: str):
    """
    Celery task to handle Jira integration logic for an alert group.
    Triggered when an alert matches a JiraIntegrationRule.
    Labels will NOT be automatically added to the Jira issue.
    Description includes the 'Occurred At' time of the specific instance.
    """
    logger.info(f"Starting Jira processing task {self.request.id} for AlertGroup ID: {alert_group_id}, Rule ID: {rule_id}, Status: {alert_status}")

    try:
        # Fetch objects from DB using IDs
        alert_group = AlertGroup.objects.get(pk=alert_group_id)
        rule = JiraIntegrationRule.objects.get(pk=rule_id)
        # Fetch the latest instance (the one that likely triggered this task)
        latest_instance = alert_group.instances.order_by('-started_at').first()
    except AlertGroup.DoesNotExist:
        logger.error(f"Task {self.request.id}: AlertGroup with ID {alert_group_id} not found. Aborting Jira task.")
        return
    except JiraIntegrationRule.DoesNotExist:
        logger.error(f"Task {self.request.id}: JiraIntegrationRule with ID {rule_id} not found. Aborting Jira task.")
        return
    except Exception as e:
        logger.error(f"Task {self.request.id}: Error fetching objects for AlertGroup {alert_group_id}: {e}", exc_info=True)
        raise

    # Instantiate JiraService
    jira_service = JiraService()

    if jira_service.client is None:
        logger.error(f"Task {self.request.id}: Jira service client not initialized (check config/connection). Aborting Jira task.")
        return

    existing_issue_key = alert_group.jira_issue_key
    issue_status_category = None

    if existing_issue_key:
        # ... (logic for checking existing issue status remains the same) ...
        logger.debug(f"Task {self.request.id}: AlertGroup {alert_group_id} has existing Jira key: {existing_issue_key}. Checking status.")
        try:
            issue_status_category = jira_service.get_issue_status_category(existing_issue_key)
        except Exception as e:
            logger.error(f"Task {self.request.id}: Failed to get status for Jira issue {existing_issue_key}: {e}", exc_info=True)
            raise e

        if issue_status_category is None and jira_service.client is not None:
            logger.warning(f"Task {self.request.id}: Could not get status for Jira issue {existing_issue_key}. Assuming it's deleted. Clearing local key.")
            alert_group.jira_issue_key = None
            try:
                alert_group.save(update_fields=['jira_issue_key'])
            except Exception as db_err:
                logger.error(f"Task {self.request.id}: Failed to clear jira_issue_key for AlertGroup {alert_group_id}: {db_err}", exc_info=True)
                raise db_err
            existing_issue_key = None

    # Read open/closed categories from settings
    open_categories = settings.JIRA_CONFIG.get('open_status_categories', ['To Do', 'In Progress'])
    closed_categories = settings.JIRA_CONFIG.get('closed_status_categories', ['Done'])

    try:
        # Logic based on alert status
        if alert_status == 'firing':
            if existing_issue_key:
                # ... (logic for adding comments to existing issues remains the same) ...
                 if issue_status_category in open_categories:
                    comment_body = f"Alert group '{alert_group.fingerprint}' is firing again at {timezone.now().isoformat()}."
                    if latest_instance and latest_instance.annotations:
                        summary = latest_instance.annotations.get('summary', 'N/A')
                        description_anno = latest_instance.annotations.get('description', 'N/A')
                        comment_body += f"\\n*Latest Summary:* {summary}\\n*Latest Description:* {description_anno}"
                    logger.info(f"Task {self.request.id}: Adding 'firing again' comment to open Jira issue: {existing_issue_key}")
                    success = jira_service.add_comment(existing_issue_key, comment_body)
                    if not success: raise Exception(f"Failed to add comment to {existing_issue_key}")
                 elif issue_status_category in closed_categories:
                    logger.info(f"Task {self.request.id}: Existing Jira issue {existing_issue_key} is closed. Clearing local key to create a new issue.")
                    alert_group.jira_issue_key = None
                    alert_group.save(update_fields=['jira_issue_key'])
                    existing_issue_key = None
                 else:
                    logger.warning(f"Task {self.request.id}: Jira issue {existing_issue_key} has unknown status category '{issue_status_category}'. Adding comment anyway.")
                    comment_body = f"Alert firing again (Jira status category '{issue_status_category}') for group '{alert_group.fingerprint}' at {timezone.now().isoformat()}."
                    success = jira_service.add_comment(existing_issue_key, comment_body)
                    if not success: raise Exception(f"Failed to add comment to {existing_issue_key}")

            # If no existing key (or cleared above), create new issue
            if not existing_issue_key:
                alert_name = alert_group.labels.get('alertname', 'N/A')
                severity = alert_group.labels.get('severity', 'default').capitalize()
                summary_anno = latest_instance.annotations.get('summary', alert_name) if latest_instance else alert_name
                jira_summary = f"[{severity}] SentryHub Alert: {summary_anno}"[:250]

                try:
                    sentryhub_url_path = reverse('alerts:alert-detail', args=[alert_group.fingerprint])
                    site_base_url = str(settings.SITE_URL).rstrip('/')
                    full_sentryhub_url = f"{site_base_url}{sentryhub_url_path}"
                except Exception as url_err:
                    logger.warning(f"Could not generate SentryHub URL: {url_err}")
                    full_sentryhub_url = "N/A (Check SITE_URL setting and URL config)"

                # --- Modify Description Parts ---
                # Get the start time of the instance that triggered this task
                occurred_at_time = latest_instance.started_at if latest_instance else alert_group.last_occurrence # Fallback to last_occurrence
                occurred_at_str = occurred_at_time.isoformat() if occurred_at_time else "N/A"

                description_parts = [
                    f"*Alert Group Fingerprint:* {alert_group.fingerprint}",
                    f"*Status:* Firing",
                    f"*Occurred At:* {occurred_at_str}", # Changed Line
                    # Removed First/Last Occurrence
                    "\\n*Labels:*",
                    "{code:json}",
                    json.dumps(alert_group.labels, indent=2, ensure_ascii=False),
                    "{code}",
                    "\\n*Annotations:*",
                    "{code:json}",
                    json.dumps(latest_instance.annotations if latest_instance else {}, indent=2, ensure_ascii=False),
                    "{code}",
                    f"\\n[View in SentryHub|{full_sentryhub_url}]"
                ]
                jira_description = "\\n".join(description_parts).strip()
                # --------------------------------

                logger.info(f"Task {self.request.id}: Creating new Jira issue for alert group {alert_group_id} in project {rule.jira_project_key}")

                # Get assignee username directly from the rule
                assignee_username = rule.assignee

                # Create issue, passing the username directly as assignee_name
                # This matches the structure confirmed to work in jira_test_issue_plan.py
                new_issue_key = jira_service.create_issue(
                    project_key=rule.jira_project_key,
                    issue_type=rule.jira_issue_type,
                    summary=jira_summary,
                    description=jira_description,
                    assignee_name=assignee_username # Pass the username from the rule
                )
                if new_issue_key:
                    alert_group.jira_issue_key = new_issue_key
                    alert_group.save(update_fields=['jira_issue_key'])
                    logger.info(f"Task {self.request.id}: Associated AlertGroup {alert_group_id} with new Jira issue {new_issue_key}")
                else:
                    logger.error(f"Task {self.request.id}: Failed to create Jira issue for AlertGroup {alert_group_id}.")
                    raise Exception(f"Jira issue creation failed for AlertGroup {alert_group_id}")

        elif alert_status == 'resolved':
            # ... (logic for resolved alerts remains the same) ...
             if existing_issue_key and issue_status_category in open_categories:
                resolved_time = timezone.now().isoformat()
                comment_body = f"Alert group '{alert_group.fingerprint}' was resolved at {resolved_time}."
                logger.info(f"Task {self.request.id}: Adding 'resolved' comment to open Jira issue: {existing_issue_key}")
                success = jira_service.add_comment(existing_issue_key, comment_body)
                if not success: raise Exception(f"Failed to add resolved comment to {existing_issue_key}")
             elif existing_issue_key:
                logger.info(f"Task {self.request.id}: Alert group {alert_group_id} resolved, but Jira issue {existing_issue_key} has status '{issue_status_category}'. No comment added.")
             else:
                logger.info(f"Task {self.request.id}: Alert group {alert_group_id} resolved, but no associated Jira issue found. No action taken.")


    except Exception as e:
        logger.error(f"Task {self.request.id}: An error occurred during Jira processing logic for AlertGroup {alert_group_id}: {e}", exc_info=True)
        raise e

    logger.info(f"Finished Jira processing task {self.request.id} for AlertGroup ID: {alert_group_id}")