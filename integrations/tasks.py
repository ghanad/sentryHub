# integrations/tasks.py

import logging
import json
import re
import pytz
from typing import Optional, Dict, Any
from celery import shared_task, Task
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.template import Context, Template, TemplateSyntaxError # Import Template components

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

# --- Helper Function for Template Rendering ---
def render_template_safe(template_string: str, context_dict: Dict[str, Any], default_value: str = "") -> str:
    """
    Safely renders a Django template string with the given context.
    Returns the default_value if the template_string is empty or rendering fails.
    """
    if not template_string:
        return default_value

    try:
        template = Template(template_string)
        rendered = template.render(Context(context_dict))
        return rendered.strip() # Remove leading/trailing whitespace
    except TemplateSyntaxError as e:
        logger.warning(f"Template syntax error during rendering: {e}. Using default value.", exc_info=True)
        return default_value
    except Exception as e:
        logger.error(f"Unexpected error during template rendering: {e}. Using default value.", exc_info=True)
        return default_value

@shared_task(bind=True, base=JiraTaskBase)
def process_jira_for_alert_group(self, alert_group_id: int, rule_id: int, alert_status: str):
    """
    Celery task to handle Jira integration logic for an alert group using templates.
    """
    logger.info(f"Starting Jira processing task {self.request.id} for AlertGroup ID: {alert_group_id}, Rule ID: {rule_id}, Status: {alert_status}")

    try:
        # Fetch objects from DB
        alert_group = AlertGroup.objects.get(pk=alert_group_id)
        rule = JiraIntegrationRule.objects.get(pk=rule_id)
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
        logger.error(f"Task {self.request.id}: Jira service client not initialized. Aborting Jira task.")
        return

    existing_issue_key = alert_group.jira_issue_key
    issue_status_category = None

    if existing_issue_key:
        # Check existing issue status
        logger.debug(f"Task {self.request.id}: AlertGroup {alert_group_id} has existing Jira key: {existing_issue_key}. Checking status.")
        try:
            issue_status_category = jira_service.get_issue_status_category(existing_issue_key)
        except Exception as e:
            logger.error(f"Task {self.request.id}: Failed to get status for Jira issue {existing_issue_key}: {e}", exc_info=True)
            raise e

        if issue_status_category is None and jira_service.client is not None:
            logger.warning(f"Task {self.request.id}: Could not get status for Jira issue {existing_issue_key}. Assuming deleted. Clearing local key.")
            alert_group.jira_issue_key = None
            try:
                alert_group.save(update_fields=['jira_issue_key'])
            except Exception as db_err:
                logger.error(f"Task {self.request.id}: Failed to clear jira_issue_key for AlertGroup {alert_group_id}: {db_err}", exc_info=True)
                raise db_err
            existing_issue_key = None

    # --- Prepare Template Context ---
    alert_name = alert_group.labels.get('alertname', 'N/A')
    severity = alert_group.labels.get('severity', 'default').capitalize()
    summary_anno = latest_instance.annotations.get('summary', alert_name) if latest_instance else alert_name
    description_anno = latest_instance.annotations.get('description', 'No description provided.') if latest_instance else 'No description provided.'
    labels_dict = alert_group.labels or {}
    annotations_dict = latest_instance.annotations if latest_instance else {}

    # SentryHub URL
    try:
        sentryhub_url_path = reverse('alerts:alert-detail', args=[alert_group.fingerprint])
        site_base_url = str(settings.SITE_URL).rstrip('/')
        full_sentryhub_url = f"{site_base_url}{sentryhub_url_path}"
    except Exception as url_err:
        logger.warning(f"Could not generate SentryHub URL: {url_err}")
        full_sentryhub_url = "N/A"

    # Occurred At Time (Formatted)
    occurred_at_time = latest_instance.started_at if latest_instance else alert_group.last_occurrence
    occurred_at_str = "N/A"
    if occurred_at_time:
        try:
            if timezone.is_naive(occurred_at_time):
                 occurred_at_time = timezone.make_aware(occurred_at_time, pytz.utc)
            tehran_tz = pytz.timezone('Asia/Tehran')
            occurred_at_local = timezone.localtime(occurred_at_time, tehran_tz)
            occurred_at_str = occurred_at_local.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as tz_err:
             logger.warning(f"Could not convert timestamp to Tehran time: {tz_err}. Falling back to ISO.")
             occurred_at_str = occurred_at_time.isoformat()

    template_context = {
        'alert_group': alert_group,
        'rule': rule,
        'alert_status': alert_status,
        'labels': labels_dict,
        'annotations': annotations_dict,
        'alertname': alert_name,
        'fingerprint': alert_group.fingerprint,
        'latest_instance': latest_instance,
        'occurred_at': occurred_at_time, # Raw datetime object
        'occurred_at_str': occurred_at_str, # Formatted string
        'sentryhub_url': full_sentryhub_url,
        'severity': severity,
        'summary_annotation': summary_anno, # Specific annotation for convenience
        'description_annotation': description_anno, # Specific annotation
        'now': timezone.now(), # Current time if needed in templates
    }
    # --- End Template Context Preparation ---

    # Read open/closed categories from settings
    open_categories = settings.JIRA_CONFIG.get('open_status_categories', ['To Do', 'In Progress'])
    closed_categories = settings.JIRA_CONFIG.get('closed_status_categories', ['Done'])

    try:
        # Logic based on alert status
        if alert_status == 'firing':
            if existing_issue_key:
                # Existing issue found, check if comment needs to be added
                 if issue_status_category in open_categories:
                    # Render comment using template
                    default_comment = f"Alert group '{alert_group.fingerprint}' is firing again at {timezone.now().isoformat()}."
                    comment_body = render_template_safe(
                        rule.jira_update_comment_template,
                        template_context,
                        default_comment
                    )
                    logger.info(f"Task {self.request.id}: Adding 'firing again' comment (from template) to open Jira issue: {existing_issue_key}")
                    success = jira_service.add_comment(existing_issue_key, comment_body)
                    if not success: raise Exception(f"Failed to add comment to {existing_issue_key}")

                 elif issue_status_category in closed_categories:
                    # Issue is closed, clear key to create a new one
                    logger.info(f"Task {self.request.id}: Existing Jira issue {existing_issue_key} is closed. Clearing local key to create a new issue.")
                    alert_group.jira_issue_key = None
                    alert_group.save(update_fields=['jira_issue_key'])
                    existing_issue_key = None # Ensure we proceed to create new issue below

                 else:
                    # Unknown status, add comment anyway (using template)
                    logger.warning(f"Task {self.request.id}: Jira issue {existing_issue_key} has unknown status category '{issue_status_category}'. Adding comment anyway.")
                    default_comment = f"Alert firing again (Jira status category '{issue_status_category}') for group '{alert_group.fingerprint}' at {timezone.now().isoformat()}."
                    comment_body = render_template_safe(
                        rule.jira_update_comment_template,
                        template_context,
                        default_comment
                    )
                    success = jira_service.add_comment(existing_issue_key, comment_body)
                    if not success: raise Exception(f"Failed to add comment to {existing_issue_key}")

            # If no existing key (or was cleared above), create a new issue
            if not existing_issue_key:
                logger.info(f"Task {self.request.id}: Creating new Jira issue for alert group {alert_group_id} in project {rule.jira_project_key} using templates.")

                # --- Use Templates for Title and Description ---
                # Render Title
                default_title = f"[{severity}] SentryHub Alert: {summary_anno}"[:250]
                jira_summary = render_template_safe(
                    rule.jira_title_template,
                    template_context,
                    default_title
                )[:255] # Ensure max length for summary

                # Render Description
                default_desc_parts = [ # Fallback similar to old logic if template fails
                    f"*Alert Group Fingerprint:* {alert_group.fingerprint}",
                    f"*Status:* Firing",
                    f"*Occurred At:* {occurred_at_str}",
                    "\\n*Labels:*",
                    "{code:json}",
                    json.dumps(labels_dict, indent=2, ensure_ascii=False),
                    "{code}",
                    "\\n*Annotations:*",
                    "{code:json}",
                    json.dumps(annotations_dict, indent=2, ensure_ascii=False),
                    "{code}",
                    f"\\n[View in SentryHub|{full_sentryhub_url}]"
                ]
                default_description = "\\n".join(default_desc_parts).strip()

                jira_description = render_template_safe(
                    rule.jira_description_template,
                    template_context,
                    default_description
                )
                # --- Start: Append SentryHub URL ---
                # Ensure the link is always added, regardless of the template content
                sentryhub_link_text = f"\n\n[View in SentryHub|{full_sentryhub_url}]"
                if sentryhub_link_text not in jira_description:
                     jira_description += sentryhub_link_text
                # --- End: Append SentryHub URL ---

                assignee_username = rule.assignee

                # Create issue using rendered content
                new_issue_key = jira_service.create_issue(
                    project_key=rule.jira_project_key,
                    issue_type=rule.jira_issue_type,
                    summary=jira_summary,
                    description=jira_description,
                    assignee_name=assignee_username
                )

                if new_issue_key:
                    alert_group.jira_issue_key = new_issue_key
                    alert_group.save(update_fields=['jira_issue_key'])
                    logger.info(f"Task {self.request.id}: Associated AlertGroup {alert_group_id} with new Jira issue {new_issue_key}")

                    # Add Watchers (logic remains the same)
                    watchers_string = rule.watchers
                    if watchers_string:
                        watcher_usernames = [w.strip() for w in watchers_string.split(',') if w.strip()]
                        if watcher_usernames:
                            logger.info(f"Task {self.request.id}: Attempting to add watchers {watcher_usernames} to issue {new_issue_key}")
                            for username in watcher_usernames:
                                try:
                                    success = jira_service.add_watcher(new_issue_key, username)
                                    if success:
                                        logger.info(f"Task {self.request.id}: Successfully added watcher '{username}' to issue {new_issue_key}")
                                    else:
                                        logger.warning(f"Task {self.request.id}: Failed to add watcher '{username}' to issue {new_issue_key} (API call returned false)")
                                except Exception as watcher_err:
                                    logger.error(f"Task {self.request.id}: Error adding watcher '{username}' to issue {new_issue_key}: {watcher_err}", exc_info=True)
                else:
                    logger.error(f"Task {self.request.id}: Failed to create Jira issue for AlertGroup {alert_group_id}.")
                    raise Exception(f"Jira issue creation failed for AlertGroup {alert_group_id}")

        elif alert_status == 'resolved':
            if existing_issue_key and issue_status_category in open_categories:
                # Render resolved comment using template
                resolved_time_iso = timezone.now().isoformat()
                default_comment = f"Alert group '{alert_group.fingerprint}' was resolved at {resolved_time_iso}."

                # Update context slightly for resolved state if needed (e.g., add resolved_time)
                template_context['resolved_time'] = timezone.now()
                template_context['resolved_time_iso'] = resolved_time_iso

                comment_body = render_template_safe(
                    rule.jira_update_comment_template, # Use the same update template
                    template_context,
                    default_comment
                )
                logger.info(f"Task {self.request.id}: Adding 'resolved' comment (from template) to open Jira issue: {existing_issue_key}")
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