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
    autoretry_for = (Exception,) # Retry on any exception for simplicity here
    retry_kwargs = {'max_retries': 3, 'countdown': 15} # Retry 3 times with 15s interval
    retry_backoff = True
    retry_jitter = True

@shared_task(bind=True, base=JiraTaskBase)
def process_jira_for_alert_group(self, alert_group_id: int, rule_id: int, alert_status: str):
    """
    Celery task to handle Jira integration logic for an alert group.
    Triggered when an alert matches a JiraIntegrationRule.
    """
    logger.info(f"Starting Jira processing task {self.request.id} for AlertGroup ID: {alert_group_id}, Rule ID: {rule_id}, Status: {alert_status}")

    try:
        # Fetch objects from DB using IDs
        alert_group = AlertGroup.objects.get(pk=alert_group_id)
        rule = JiraIntegrationRule.objects.get(pk=rule_id)
        latest_instance = alert_group.instances.order_by('-started_at').first()
    except AlertGroup.DoesNotExist:
        logger.error(f"Task {self.request.id}: AlertGroup with ID {alert_group_id} not found. Aborting Jira task.")
        return # Stop task if AlertGroup not found
    except JiraIntegrationRule.DoesNotExist:
        logger.error(f"Task {self.request.id}: JiraIntegrationRule with ID {rule_id} not found. Aborting Jira task.")
        return # Stop task if Rule not found
    except Exception as e:
        logger.error(f"Task {self.request.id}: Error fetching objects for AlertGroup {alert_group_id}: {e}", exc_info=True)
        raise # Re-raise to trigger Celery retry

    # Instantiate JiraService
    jira_service = JiraService()

    # --- Check if client was initialized ---
    if jira_service.client is None:
        logger.error(f"Task {self.request.id}: Jira service client not initialized (check config/connection). Aborting Jira task.")
        return
    # ---------------------------------------

    existing_issue_key = alert_group.jira_issue_key
    issue_status_category = None

    if existing_issue_key:
        logger.debug(f"Task {self.request.id}: AlertGroup {alert_group_id} has existing Jira key: {existing_issue_key}. Checking status.")
        try:
            issue_status_category = jira_service.get_issue_status_category(existing_issue_key)
        except Exception as e:
            logger.error(f"Task {self.request.id}: Failed to get status for Jira issue {existing_issue_key}: {e}", exc_info=True)
            raise e # Re-raise to trigger Celery retry

        # If status is None (e.g., issue deleted) and client seems ok, clear local key
        if issue_status_category is None and jira_service.client is not None:
            logger.warning(f"Task {self.request.id}: Could not get status for Jira issue {existing_issue_key}. Assuming it's deleted. Clearing local key.")
            alert_group.jira_issue_key = None
            try:
                alert_group.save(update_fields=['jira_issue_key'])
            except Exception as db_err:
                logger.error(f"Task {self.request.id}: Failed to clear jira_issue_key for AlertGroup {alert_group_id}: {db_err}", exc_info=True)
                raise db_err # Re-raise to trigger Celery retry
            existing_issue_key = None

    # Read open/closed categories from settings
    open_categories = settings.JIRA_CONFIG.get('open_status_categories', ['To Do', 'In Progress'])
    closed_categories = settings.JIRA_CONFIG.get('closed_status_categories', ['Done'])

    try:
        # Logic based on alert status (firing or resolved)
        if alert_status == 'firing':
            if existing_issue_key:
                if issue_status_category in open_categories:
                    # Add comment to existing open issue
                    comment_body = f"Alert group '{alert_group.fingerprint}' is firing again at {timezone.now().isoformat()}."
                    if latest_instance and latest_instance.annotations:
                        summary = latest_instance.annotations.get('summary', 'N/A')
                        description_anno = latest_instance.annotations.get('description', 'N/A')
                        comment_body += f"\\n*Latest Summary:* {summary}\\n*Latest Description:* {description_anno}"
                    logger.info(f"Task {self.request.id}: Adding 'firing again' comment to open Jira issue: {existing_issue_key}")
                    success = jira_service.add_comment(existing_issue_key, comment_body)
                    if not success: raise Exception(f"Failed to add comment to {existing_issue_key}")
                elif issue_status_category in closed_categories:
                    # Clear local key if issue is closed, new one will be created below
                    logger.info(f"Task {self.request.id}: Existing Jira issue {existing_issue_key} is closed. Clearing local key to create a new issue.")
                    alert_group.jira_issue_key = None
                    alert_group.save(update_fields=['jira_issue_key'])
                    existing_issue_key = None # Ensure it's None for the next check
                else:
                     # Issue status unknown, add comment anyway
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

                # Build description using \n for newlines (handled by JiraService ADF)
                description_parts = [
                    f"*Alert Group Fingerprint:* {alert_group.fingerprint}",
                    f"*Status:* Firing",
                    f"*First Occurrence:* {alert_group.first_occurrence.isoformat()}",
                    f"*Last Occurrence:* {alert_group.last_occurrence.isoformat()}",
                    "\\n*Labels:*",
                    "{code:json}", # ADF code block hint
                    json.dumps(alert_group.labels, indent=2, ensure_ascii=False),
                    "{code}",
                    "\\n*Annotations:*",
                    "{code:json}",
                    json.dumps(latest_instance.annotations if latest_instance else {}, indent=2, ensure_ascii=False),
                    "{code}",
                    f"\\n[View in SentryHub|{full_sentryhub_url}]"
                ]
                jira_description = "\\n".join(description_parts).strip()

                logger.info(f"Task {self.request.id}: Creating new Jira issue for alert group {alert_group_id} in project {rule.jira_project_key}")
                # Prepare labels
                jira_labels = ['sentryhub', alert_group.labels.get('severity', 'default')]
                for key, value in alert_group.labels.items():
                    sanitized_label = re.sub(r'[^a-zA-Z0-9_-]+', '_', f"{key}_{value}")[:255]
                    if len(sanitized_label) > 0:
                        jira_labels.append(sanitized_label)

                extra_fields = {'labels': list(set(jira_labels))}

                # Create issue
                new_issue_key = jira_service.create_issue(
                    project_key=rule.jira_project_key,
                    issue_type=rule.jira_issue_type,
                    summary=jira_summary,
                    description=jira_description,
                    **extra_fields
                )
                if new_issue_key:
                    alert_group.jira_issue_key = new_issue_key
                    alert_group.save(update_fields=['jira_issue_key'])
                    logger.info(f"Task {self.request.id}: Associated AlertGroup {alert_group_id} with new Jira issue {new_issue_key}")
                else:
                    logger.error(f"Task {self.request.id}: Failed to create Jira issue for AlertGroup {alert_group_id}.")
                    raise Exception(f"Jira issue creation failed for AlertGroup {alert_group_id}")

        elif alert_status == 'resolved':
            if existing_issue_key and issue_status_category in open_categories:
                 # Add resolved comment to open issue
                resolved_time = timezone.now().isoformat()
                comment_body = f"Alert group '{alert_group.fingerprint}' was resolved at {resolved_time}."
                logger.info(f"Task {self.request.id}: Adding 'resolved' comment to open Jira issue: {existing_issue_key}")
                success = jira_service.add_comment(existing_issue_key, comment_body)
                if not success: raise Exception(f"Failed to add resolved comment to {existing_issue_key}")
            elif existing_issue_key:
                logger.info(f"Task {self.request.id}: Alert group {alert_group_id} resolved, but Jira issue {existing_issue_key} has status '{issue_status_category}'. No comment added.")
            else:
                logger.info(f"Task {self.request.id}: Alert group {alert_group_id} resolved, but no associated Jira issue found. No action taken.")

    # Catch any exception within the main logic block
    except Exception as e:
        logger.error(f"Task {self.request.id}: An error occurred during Jira processing logic for AlertGroup {alert_group_id}: {e}", exc_info=True)
        raise e # Re-raise to trigger Celery retry

    # Log successful completion
    logger.info(f"Finished Jira processing task {self.request.id} for AlertGroup ID: {alert_group_id}")