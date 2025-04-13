import logging
import json
from typing import Optional, Dict, Any

from celery import shared_task, Task
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist

from .services.jira_service import JiraService
from .models import AlertGroup, JiraIntegrationRule, AlertInstance

logger = logging.getLogger(__name__)

# Base task with retry logic for API calls might be useful
class JiraTaskBase(Task):
    # Example: Retry on common transient errors (adjust exceptions as needed)
    # autoretry_for = (ConnectionError, TimeoutError) # Add relevant JiraError status codes if possible
    retry_kwargs = {'max_retries': 3, 'countdown': 15} # Example: Retry 3 times, wait 15s
    retry_backoff = True
    retry_jitter = True # Add randomness to wait time


@shared_task(bind=True, base=JiraTaskBase) # Use bind=True for self (task instance) access
def process_jira_for_alert_group(self, alert_group_id: int, rule_id: int, alert_status: str):
    """
    Main Celery task to handle Jira integration logic for an alert group.
    Triggered when an alert matches a JiraIntegrationRule.

    Args:
        self: The task instance (due to bind=True).
        alert_group_id: The ID of the AlertGroup.
        rule_id: The ID of the matching JiraIntegrationRule.
        alert_status: The current status of the alert ('firing' or 'resolved').
    """
    logger.info(f"Starting Jira processing task {self.request.id} for AlertGroup ID: {alert_group_id}, Rule ID: {rule_id}, Status: {alert_status}")

    try:
        alert_group = AlertGroup.objects.select_related('silence_rule').get(pk=alert_group_id)
        rule = JiraIntegrationRule.objects.get(pk=rule_id)
        # Get the latest instance for context
        latest_instance = alert_group.instances.order_by('-received_at').first()
    except AlertGroup.DoesNotExist:
        logger.error(f"Task {self.request.id}: AlertGroup with ID {alert_group_id} not found. Aborting Jira task.")
        return # No retry needed if object doesn't exist
    except JiraIntegrationRule.DoesNotExist:
        logger.error(f"Task {self.request.id}: JiraIntegrationRule with ID {rule_id} not found. Aborting Jira task.")
        return # No retry needed
    except Exception as e:
         logger.error(f"Task {self.request.id}: Error fetching objects for AlertGroup {alert_group_id}: {e}", exc_info=True)
         # May want to retry depending on the error
         raise # Reraise to potentially trigger retry

    jira_service = JiraService()
    if not jira_service.is_configured:
        logger.error(f"Task {self.request.id}: Jira service not configured. Aborting Jira task.")
        # No retry if config is missing.
        return

    existing_issue_key = alert_group.jira_issue_key
    issue_status_category = None

    if existing_issue_key:
        logger.debug(f"Task {self.request.id}: AlertGroup {alert_group_id} has existing Jira key: {existing_issue_key}. Checking status.")
        try:
             issue_status_category = jira_service.get_issue_status_category(existing_issue_key)
        except Exception as e:
             logger.error(f"Task {self.request.id}: Failed to get status for Jira issue {existing_issue_key}: {e}", exc_info=True)
             # Trigger retry? Could be a transient API issue.
             self.retry(exc=e) # Use Celery's retry mechanism

        if issue_status_category is None and jira_service.is_configured: # Handle case where status check failed definitively (e.g., 404)
            logger.warning(f"Task {self.request.id}: Could not get status for Jira issue {existing_issue_key} (possibly deleted or inaccessible). Clearing local key.")
            alert_group.jira_issue_key = None
            try:
                alert_group.save(update_fields=['jira_issue_key'])
            except Exception as db_err:
                logger.error(f"Task {self.request.id}: Failed to clear jira_issue_key for AlertGroup {alert_group_id} after status check failure: {db_err}", exc_info=True)
                self.retry(exc=db_err) # Retry on DB error
            existing_issue_key = None # Proceed as if no key existed


    # --- Logic based on alert status and Jira issue status ---

    open_categories = settings.JIRA_CONFIG.get('open_status_categories', ['To Do', 'In Progress'])
    closed_categories = settings.JIRA_CONFIG.get('closed_status_categories', ['Done'])

    try: # Wrap main logic in try/except for retry handling
        if alert_status == 'firing':
            if existing_issue_key:
                if issue_status_category in open_categories:
                    # Issue exists and is open: Add a comment
                    comment = f"Alert group '{alert_group.fingerprint}' is firing again at {timezone.now().isoformat()}."
                    if latest_instance:
                         comment += f"\nLatest details summary: {latest_instance.summary or 'N/A'}"
                    logger.info(f"Task {self.request.id}: Adding 'firing again' comment to open Jira issue: {existing_issue_key}")
                    success = jira_service.add_comment(existing_issue_key, comment)
                    if not success: raise Exception(f"Failed to add comment to {existing_issue_key}")
                    # Potentially update other fields (e.g., last_seen custom field) here
                elif issue_status_category in closed_categories:
                    # Issue exists but is closed: Create a NEW issue
                    logger.info(f"Task {self.request.id}: Existing Jira issue {existing_issue_key} is closed. Creating a new issue for firing alert group {alert_group_id}.")
                    alert_group.jira_issue_key = None # Clear old key before creating new
                    alert_group.save(update_fields=['jira_issue_key'])
                    # Fall through to the 'create new issue' block below
                else:
                     # Status is neither clearly open nor closed (or unknown category)
                     logger.warning(f"Task {self.request.id}: Jira issue {existing_issue_key} has status category '{issue_status_category}'. Adding comment anyway.")
                     comment = f"Alert firing again (status category '{issue_status_category}') for group '{alert_group.fingerprint}' at {timezone.now().isoformat()}."
                     success = jira_service.add_comment(existing_issue_key, comment)
                     if not success: raise Exception(f"Failed to add comment to {existing_issue_key} (unknown status)")

            if not alert_group.jira_issue_key: # Handles 'no key initially' and 'key cleared'
                # Create a new issue
                alert_name = alert_group.get_common_label('alertname', 'N/A')
                severity = alert_group.get_common_label('severity', 'default').capitalize()
                summary = f"[{severity}] SentryHub Alert: {latest_instance.summary if latest_instance else alert_name}"[:250] # Limit summary length

                # Construct description with more details using Jira Markdown (subset of ADF)
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
                # Add extra fields like labels based on alert labels if desired
                jira_labels = ['sentryhub', alert_group.get_common_label('severity', 'default')]
                # Add more labels from the alert if needed, ensure they are valid Jira labels (no spaces etc.)
                for key, value in alert_group.labels.items():
                     # Basic sanitization for Jira labels
                     sanitized_label = re.sub(r'[^\w-]+', '_', f"{key}_{value}")[:255]
                     if len(sanitized_label) > 0:
                          jira_labels.append(sanitized_label)

                extra_fields = {'labels': list(set(jira_labels))} # Use set to remove duplicates

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
                    # Creation failed, task might retry based on base class
                    logger.error(f"Task {self.request.id}: Failed to create Jira issue for AlertGroup {alert_group_id}.")
                    raise Exception(f"Jira issue creation failed for AlertGroup {alert_group_id}")


        elif alert_status == 'resolved':
            if existing_issue_key and issue_status_category in open_categories:
                # Issue exists and is open: Add a 'resolved' comment
                resolved_time = timezone.now().isoformat()
                comment = f"Alert group '{alert_group.fingerprint}' was resolved at {resolved_time}."
                logger.info(f"Task {self.request.id}: Adding 'resolved' comment to open Jira issue: {existing_issue_key}")
                success = jira_service.add_comment(existing_issue_key, comment)
                if not success: raise Exception(f"Failed to add resolved comment to {existing_issue_key}")
                # Consider if you want to automatically transition the Jira issue status here (more complex)
                # Or maybe automatically clear the local key? Depends on desired workflow.
                # For now, just add comment. Manual closure in Jira is often preferred.
            elif existing_issue_key:
                logger.info(f"Task {self.request.id}: Alert group {alert_group_id} resolved, but Jira issue {existing_issue_key} has status '{issue_status_category}'. No comment added.")
            else:
                logger.info(f"Task {self.request.id}: Alert group {alert_group_id} resolved, but no associated Jira issue found. No action taken.")

    except Exception as e:
        # Catch exceptions during the main logic (API calls, DB saves)
        logger.error(f"Task {self.request.id}: An error occurred during Jira processing for AlertGroup {alert_group_id}: {e}", exc_info=True)
        # Retry the task using Celery's mechanism
        self.retry(exc=e)

    logger.info(f"Finished Jira processing task {self.request.id} for AlertGroup ID: {alert_group_id}")