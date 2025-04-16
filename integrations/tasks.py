import logging
import json
import re
from typing import Optional, Dict, Any

from celery import shared_task, Task
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist

from integrations.services.jira_service import JiraService
from integrations.models import JiraIntegrationRule
from alerts.models import AlertGroup, AlertInstance

logger = logging.getLogger(__name__)

# Base task with retry logic for API calls
class JiraTaskBase(Task):
    retry_kwargs = {'max_retries': 3, 'countdown': 15}
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
        alert_group = AlertGroup.objects.select_related('silence_rule').get(pk=alert_group_id)
        rule = JiraIntegrationRule.objects.get(pk=rule_id)
        latest_instance = alert_group.instances.order_by('-received_at').first()
    except AlertGroup.DoesNotExist:
        logger.error(f"Task {self.request.id}: AlertGroup with ID {alert_group_id} not found. Aborting Jira task.")
        return
    except JiraIntegrationRule.DoesNotExist:
        logger.error(f"Task {self.request.id}: JiraIntegrationRule with ID {rule_id} not found. Aborting Jira task.")
        return
    except Exception as e:
        logger.error(f"Task {self.request.id}: Error fetching objects for AlertGroup {alert_group_id}: {e}", exc_info=True)
        raise

    jira_service = JiraService()
    if not jira_service.is_configured:
        logger.error(f"Task {self.request.id}: Jira service not configured. Aborting Jira task.")
        return

    existing_issue_key = alert_group.jira_issue_key
    issue_status_category = None

    if existing_issue_key:
        logger.debug(f"Task {self.request.id}: AlertGroup {alert_group_id} has existing Jira key: {existing_issue_key}. Checking status.")
        try:
            issue_status_category = jira_service.get_issue_status_category(existing_issue_key)
        except Exception as e:
            logger.error(f"Task {self.request.id}: Failed to get status for Jira issue {existing_issue_key}: {e}", exc_info=True)
            self.retry(exc=e)

        if issue_status_category is None and jira_service.is_configured:
            logger.warning(f"Task {self.request.id}: Could not get status for Jira issue {existing_issue_key}. Clearing local key.")
            alert_group.jira_issue_key = None
            try:
                alert_group.save(update_fields=['jira_issue_key'])
            except Exception as db_err:
                logger.error(f"Task {self.request.id}: Failed to clear jira_issue_key: {db_err}", exc_info=True)
                self.retry(exc=db_err)
            existing_issue_key = None

    open_categories = settings.JIRA_CONFIG.get('open_status_categories', ['To Do', 'In Progress'])
    closed_categories = settings.JIRA_CONFIG.get('closed_status_categories', ['Done'])

    try:
        if alert_status == 'firing':
            if existing_issue_key:
                if issue_status_category in open_categories:
                    comment = f"Alert group '{alert_group.fingerprint}' is firing again at {timezone.now().isoformat()}."
                    if latest_instance:
                        comment += f"\nLatest details summary: {latest_instance.summary or 'N/A'}"
                    logger.info(f"Task {self.request.id}: Adding 'firing again' comment to open Jira issue: {existing_issue_key}")
                    success = jira_service.add_comment(existing_issue_key, comment)
                    if not success: raise Exception(f"Failed to add comment to {existing_issue_key}")
                elif issue_status_category in closed_categories:
                    logger.info(f"Task {self.request.id}: Existing Jira issue {existing_issue_key} is closed. Creating new issue.")
                    alert_group.jira_issue_key = None
                    alert_group.save(update_fields=['jira_issue_key'])
                else:
                    logger.warning(f"Task {self.request.id}: Jira issue {existing_issue_key} has status category '{issue_status_category}'. Adding comment anyway.")
                    comment = f"Alert firing again (status category '{issue_status_category}') for group '{alert_group.fingerprint}' at {timezone.now().isoformat()}."
                    success = jira_service.add_comment(existing_issue_key, comment)
                    if not success: raise Exception(f"Failed to add comment to {existing_issue_key}")

            if not alert_group.jira_issue_key:
                alert_name = alert_group.get_common_label('alertname', 'N/A')
                severity = alert_group.get_common_label('severity', 'default').capitalize()
                summary = f"[{severity}] SentryHub Alert: {latest_instance.summary if latest_instance else alert_name}"[:250]

                try:
                    sentryhub_url_path = reverse('alerts:alert_detail', args=[alert_group.fingerprint])
                    full_sentryhub_url = f"{settings.SITE_URL}{sentryhub_url_path}"
                except Exception:
                    full_sentryhub_url = "N/A (Check SITE_URL setting and URL config)"

                description_parts = [
                    f"*Alert Group Fingerprint:* {alert_group.fingerprint}",
                    f"*Status:* Firing",
                    f"*First Seen:* {alert_group.first_seen.isoformat()}",
                    f"*Last Seen:* {alert_group.last_seen.isoformat()}",
                    "\n*Labels:*",
                    "{code:json}",
                    json.dumps(alert_group.labels, indent=2),
                    "{code}",
                    "\n*Annotations:*",
                    "{code:json}",
                    json.dumps(alert_group.annotations, indent=2),
                    "{code}",
                    f"\n*Latest Alert Summary:* {latest_instance.summary if latest_instance else 'N/A'}",
                    f"*Latest Alert Description:* {latest_instance.description if latest_instance else 'N/A'}",
                    f"\n[Link to SentryHub|{full_sentryhub_url}]"
                ]
                description = "\n".join(description_parts)

                logger.info(f"Task {self.request.id}: Creating new Jira issue for alert group {alert_group_id} in project {rule.jira_project_key}")
                jira_labels = ['sentryhub', alert_group.get_common_label('severity', 'default')]
                for key, value in alert_group.labels.items():
                    sanitized_label = re.sub(r'[^\w-]+', '_', f"{key}_{value}")[:255]
                    if len(sanitized_label) > 0:
                        jira_labels.append(sanitized_label)

                extra_fields = {'labels': list(set(jira_labels))}

                new_issue_key = jira_service.create_issue(
                    project_key=rule.jira_project_key,
                    issue_type=rule.jira_issue_type,
                    summary=summary,
                    description=description.strip(),
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
                resolved_time = timezone.now().isoformat()
                comment = f"Alert group '{alert_group.fingerprint}' was resolved at {resolved_time}."
                logger.info(f"Task {self.request.id}: Adding 'resolved' comment to open Jira issue: {existing_issue_key}")
                success = jira_service.add_comment(existing_issue_key, comment)
                if not success: raise Exception(f"Failed to add resolved comment to {existing_issue_key}")
            elif existing_issue_key:
                logger.info(f"Task {self.request.id}: Alert group {alert_group_id} resolved, but Jira issue {existing_issue_key} has status '{issue_status_category}'. No comment added.")
            else:
                logger.info(f"Task {self.request.id}: Alert group {alert_group_id} resolved, but no associated Jira issue found. No action taken.")

    except Exception as e:
        logger.error(f"Task {self.request.id}: An error occurred during Jira processing for AlertGroup {alert_group_id}: {e}", exc_info=True)
        raise e # Re-raise the exception to mark the task as failed immediately

    logger.info(f"Finished Jira processing task {self.request.id} for AlertGroup ID: {alert_group_id}")