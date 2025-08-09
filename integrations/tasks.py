# integrations/tasks.py

import logging
import json
import re
import pytz
from typing import Optional, Dict, Any
from celery import shared_task, Task
from django.conf import settings

from core.services.metrics import metrics_manager
from integrations.exceptions import SlackNotificationError
from django.utils import timezone
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.template import Context, Template, TemplateSyntaxError

from integrations.models import JiraIntegrationRule, SlackIntegrationRule
from alerts.models import AlertGroup, AlertInstance # AlertInstance is imported
from integrations.services.jira_service import JiraService
from integrations.services.slack_service import SlackService

# jira created time: https://aistudio.google.com/prompts/11xHhaYXIUhCDXxiYOsnUnByzQfZTtZWk


logger = logging.getLogger(__name__)

# Base task with retry logic (unchanged)
class JiraTaskBase(Task):
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3, 'countdown': 15}
    retry_backoff = True
    retry_jitter = True

# --- Helper Function for Template Rendering --- (unchanged)
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
        return rendered.strip()
    except TemplateSyntaxError as e:
        logger.warning(f"Template syntax error during rendering: {e}. Using default value.", exc_info=True)
        return default_value
    except Exception as e:
        logger.error(f"Unexpected error during template rendering: {e}. Using default value.", exc_info=True)
        return default_value

@shared_task(bind=True, base=JiraTaskBase)
def process_jira_for_alert_group(self, alert_group_id: int, rule_id: int, alert_status: str, triggering_instance_id: Optional[int] = None):
    """
    Celery task to handle Jira integration logic for an alert group using templates.
    Uses the specific triggering_instance if provided.
    """
    try:
        alert_group = AlertGroup.objects.get(pk=alert_group_id)
        rule = JiraIntegrationRule.objects.get(pk=rule_id)
        fingerprint_for_log = alert_group.fingerprint
        logger.info(f"Jira Task {self.request.id} (FP: {fingerprint_for_log}): Starting for AlertGroup ID: {alert_group_id}, Rule ID: {rule_id}, Status: {alert_status}, TriggeringInstanceID: {triggering_instance_id}")
    except AlertGroup.DoesNotExist:
        logger.error(f"Task {self.request.id}: AlertGroup with ID {alert_group_id} not found. Aborting Jira task.")
        return
    except JiraIntegrationRule.DoesNotExist:
        logger.error(f"Task {self.request.id}: JiraIntegrationRule with ID {rule_id} not found. Aborting Jira task.")
        return
    except Exception as e:
        logger.error(f"Task {self.request.id}: Error fetching base objects for AlertGroup {alert_group_id}: {e}", exc_info=True)
        raise # Re-raise to allow Celery retry

    # Log the received triggering_instance_id more explicitly
    logger.info(f"Jira Task {self.request.id} (FP: {fingerprint_for_log}): Received TriggeringInstanceID: {triggering_instance_id}")

    current_event_instance = None
    if triggering_instance_id:
        try:
            current_event_instance = AlertInstance.objects.get(pk=triggering_instance_id)
            logger.info(f"Jira Task {self.request.id} (FP: {fingerprint_for_log}): Successfully fetched Triggering AlertInstance ID: {triggering_instance_id}, Started at: {current_event_instance.started_at}")
        except AlertInstance.DoesNotExist:
            logger.warning(f"Jira Task {self.request.id} (FP: {fingerprint_for_log}): Triggering AlertInstance with ID {triggering_instance_id} not found. Will rely on latest_instance or group data.")
    else:
        logger.info(f"Jira Task {self.request.id} (FP: {fingerprint_for_log}): TriggeringInstanceID was None.")


    latest_overall_instance = alert_group.instances.order_by('-started_at').first()
    if latest_overall_instance:
        logger.info(f"Jira Task {self.request.id} (FP: {fingerprint_for_log}): Latest overall instance for group: ID={latest_overall_instance.id}, Started_at={latest_overall_instance.started_at}")
    else:
        logger.info(f"Jira Task {self.request.id} (FP: {fingerprint_for_log}): No overall instances found for this group.")


    instance_for_context = current_event_instance if current_event_instance else latest_overall_instance
    if instance_for_context:
        logger.info(f"Jira Task {self.request.id} (FP: {fingerprint_for_log}): Instance selected for context: ID={instance_for_context.id}, Started_at={instance_for_context.started_at}")
    else:
        logger.warning(f"Jira Task {self.request.id} (FP: {fingerprint_for_log}): No instance could be selected for context. Annotations might be empty and occurred_at will use group's last_occurrence.")


    jira_service = JiraService()
    if jira_service.client is None:
        logger.error(f"Task {self.request.id} (FP: {fingerprint_for_log}): Jira service client not initialized. Aborting Jira task.")
        return

    existing_issue_key = alert_group.jira_issue_key
    issue_status_category = None

    if existing_issue_key:
        logger.info(f"Jira Task {self.request.id} (FP: {fingerprint_for_log}): AlertGroup has existing Jira key: {existing_issue_key}. Checking status.")
        try:
            issue_status_category = jira_service.get_issue_status_category(existing_issue_key)
        except Exception as e:
            logger.error(f"Jira Task {self.request.id} (FP: {fingerprint_for_log}): Failed to get status for Jira issue {existing_issue_key}: {e}", exc_info=True)
            raise e

        if issue_status_category is None and jira_service.client is not None:
            logger.warning(f"Jira Task {self.request.id} (FP: {fingerprint_for_log}): Could not get status for Jira issue {existing_issue_key} (it might have been deleted). Clearing local key.")
            alert_group.jira_issue_key = None
            try:
                alert_group.save(update_fields=['jira_issue_key'])
            except Exception as db_err:
                logger.error(f"Jira Task {self.request.id} (FP: {fingerprint_for_log}): Failed to clear jira_issue_key for AlertGroup {alert_group_id}: {db_err}", exc_info=True)
                raise db_err
            existing_issue_key = None

    alert_name = alert_group.labels.get('alertname', 'N/A')
    severity = alert_group.labels.get('severity', 'default').capitalize()

    annotations_dict = instance_for_context.annotations if instance_for_context else {}
    summary_anno = annotations_dict.get('summary', alert_name)
    description_anno = annotations_dict.get('description', 'No description provided.')

    labels_dict = alert_group.labels or {}

    try:
        sentryhub_url_path = reverse('alerts:alert-detail', args=[alert_group.fingerprint])
        site_base_url = str(settings.SITE_URL).rstrip('/')
        full_sentryhub_url = f"{site_base_url}{sentryhub_url_path}"
    except Exception as url_err:
        logger.warning(f"Jira Task {self.request.id} (FP: {fingerprint_for_log}): Could not generate SentryHub URL: {url_err}")
        full_sentryhub_url = "N/A"

    occurred_at_time = instance_for_context.started_at if instance_for_context else alert_group.last_occurrence
    logger.info(f"Jira Task {self.request.id} (FP: {fingerprint_for_log}): occurred_at_time before formatting = {occurred_at_time} (Type: {type(occurred_at_time)})") # Log before formatting
    occurred_at_str = "N/A"
    if occurred_at_time:
        try:
            if timezone.is_naive(occurred_at_time):
                 occurred_at_time = timezone.make_aware(occurred_at_time, pytz.utc)
            tehran_tz = pytz.timezone('Asia/Tehran')
            occurred_at_local = timezone.localtime(occurred_at_time, tehran_tz)
            occurred_at_str = occurred_at_local.strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"Jira Task {self.request.id} (FP: {fingerprint_for_log}): occurred_at_str after formatting = {occurred_at_str}") # Log after formatting
        except Exception as tz_err:
             logger.warning(f"Jira Task {self.request.id} (FP: {fingerprint_for_log}): Could not convert occurred_at_time to target timezone: {tz_err}. Falling back to ISO.", exc_info=True)
             occurred_at_str = occurred_at_time.isoformat() if occurred_at_time else "N/A"
    else:
        logger.warning(f"Jira Task {self.request.id} (FP: {fingerprint_for_log}): occurred_at_time was None.")


    current_task_time = timezone.now()

    template_context = {
        'alert_group': alert_group,
        'rule': rule,
        'alert_status': alert_status,
        'labels': labels_dict,
        'annotations': annotations_dict,
        'alertname': alert_name,
        'fingerprint': alert_group.fingerprint,
        'current_event_instance': current_event_instance,
        'latest_instance': latest_overall_instance,
        'occurred_at': occurred_at_time,
        'occurred_at_str': occurred_at_str,
        'sentryhub_url': full_sentryhub_url,
        'severity': severity,
        'summary_annotation': summary_anno,
        'description_annotation': description_anno,
        'now': current_task_time,
        'resolved_time': current_task_time if alert_status == 'resolved' else None,
    }
    logger.info(f"Jira Task {self.request.id} (FP: {fingerprint_for_log}): Final template_context['occurred_at_str'] = {template_context['occurred_at_str']}")


    open_categories = settings.JIRA_CONFIG.get('open_status_categories', ['To Do', 'In Progress'])
    closed_categories = settings.JIRA_CONFIG.get('closed_status_categories', ['Done'])

    try:
        if alert_status == 'firing':
            if existing_issue_key:
                 if issue_status_category in open_categories:
                    default_comment = f"Alert group '{alert_group.fingerprint}' is firing again (task run at {current_task_time.isoformat()})."
                    comment_body = render_template_safe(rule.jira_update_comment_template, template_context, default_comment)
                    logger.info(f"Jira Task {self.request.id} (FP: {fingerprint_for_log}): Adding 'firing again' comment to open Jira issue: {existing_issue_key}")
                    success = jira_service.add_comment(existing_issue_key, comment_body)
                    if not success: raise Exception(f"Failed to add 'firing again' comment to {existing_issue_key}")
                 elif issue_status_category in closed_categories:
                    logger.info(f"Jira Task {self.request.id} (FP: {fingerprint_for_log}): Existing Jira issue {existing_issue_key} is closed. Clearing local key to create a new issue.")
                    alert_group.jira_issue_key = None
                    alert_group.save(update_fields=['jira_issue_key'])
                    existing_issue_key = None
                 else:
                    logger.warning(f"Jira Task {self.request.id} (FP: {fingerprint_for_log}): Jira issue {existing_issue_key} has unknown status category '{issue_status_category}'. Adding 'firing again' comment as precaution.")
                    default_comment = f"Alert firing again (Jira status category '{issue_status_category}', task run at {current_task_time.isoformat()}) for group '{alert_group.fingerprint}'."
                    comment_body = render_template_safe(rule.jira_update_comment_template, template_context, default_comment)
                    success = jira_service.add_comment(existing_issue_key, comment_body)
                    if not success: raise Exception(f"Failed to add comment (unknown status) to {existing_issue_key}")

            if not existing_issue_key:
                logger.info(f"Jira Task {self.request.id} (FP: {fingerprint_for_log}): Creating new Jira issue in project {rule.jira_project_key} for AlertGroup ID: {alert_group_id}.")
                default_title = f"[{severity}] SentryHub Alert: {summary_anno}"[:250]
                jira_summary = render_template_safe(rule.jira_title_template, template_context, default_title)[:255]

                default_desc_parts = [
                    f"*Alert Group Fingerprint:* {alert_group.fingerprint}",
                    f"*Status:* Firing",
                    f"*Occurred At (Instance/Group):* {occurred_at_str}",
                    "\\n*Labels:*", "{code:json}", json.dumps(labels_dict, indent=2, ensure_ascii=False), "{code}",
                    "\\n*Annotations (from relevant instance):*", "{code:json}", json.dumps(annotations_dict, indent=2, ensure_ascii=False), "{code}",
                    f"\\n[View in SentryHub|{full_sentryhub_url}]"
                ]
                default_description = "\\n".join(default_desc_parts).strip()
                jira_description = render_template_safe(rule.jira_description_template, template_context, default_description)

                sentryhub_link_text = f"\n\n[View in SentryHub|{full_sentryhub_url}]"
                if sentryhub_link_text not in jira_description:
                     jira_description += sentryhub_link_text

                assignee_username = rule.assignee

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
                    logger.info(f"Task {self.request.id} (FP: {fingerprint_for_log}): Associated AlertGroup with new Jira issue {new_issue_key}")

                    watchers_string = rule.watchers
                    if watchers_string:
                        watcher_usernames = [w.strip() for w in watchers_string.split(',') if w.strip()]
                        if watcher_usernames:
                            logger.info(f"Task {self.request.id} (FP: {fingerprint_for_log}): Attempting to add watchers {watcher_usernames} to issue {new_issue_key}")
                            for username in watcher_usernames:
                                try:
                                    if not jira_service.add_watcher(new_issue_key, username):
                                        logger.warning(f"Task {self.request.id} (FP: {fingerprint_for_log}): Failed to add watcher '{username}' to issue {new_issue_key} (API call returned false or error)")
                                except Exception as watcher_err:
                                    logger.error(f"Task {self.request.id} (FP: {fingerprint_for_log}): Error adding watcher '{username}' to issue {new_issue_key}: {watcher_err}", exc_info=True)
                else:
                    logger.error(f"Jira Task {self.request.id} (FP: {fingerprint_for_log}): Failed to create Jira issue for AlertGroup {alert_group_id}.")
                    raise Exception(f"Jira issue creation failed for AlertGroup {alert_group_id}")

        elif alert_status == 'resolved':
            if existing_issue_key and issue_status_category in open_categories:
                default_comment = f"Alert group '{alert_group.fingerprint}' was resolved (task run at {current_task_time.isoformat()})."
                comment_body = render_template_safe(rule.jira_update_comment_template, template_context, default_comment)
                logger.info(f"Jira Task {self.request.id} (FP: {fingerprint_for_log}): Adding 'resolved' comment to open Jira issue: {existing_issue_key}")
                success = jira_service.add_comment(existing_issue_key, comment_body)
                if not success: raise Exception(f"Failed to add 'resolved' comment to {existing_issue_key}")
            elif existing_issue_key:
                logger.info(f"Jira Task {self.request.id} (FP: {fingerprint_for_log}): AlertGroup resolved, but Jira issue {existing_issue_key} has status '{issue_status_category}' (not open). No comment added.")
            else:
                logger.info(f"Jira Task {self.request.id} (FP: {fingerprint_for_log}): AlertGroup resolved, but no associated Jira issue found. No action taken.")

    except Exception as e:
        logger.error(f"Jira Task {self.request.id} (FP: {fingerprint_for_log}): An unhandled error occurred during Jira processing logic for AlertGroup {alert_group_id}: {e}", exc_info=True)
        raise e

    logger.info(f"Jira Task {self.request.id} (FP: {fingerprint_for_log}): Finished processing for AlertGroup ID: {alert_group_id}")


@shared_task(bind=True, autoretry_for=(SlackNotificationError,), retry_kwargs={'max_retries': 12}, countdown=300, retry_backoff=True, retry_backoff_max=3600)
def process_slack_for_alert_group(self, alert_group_id: int, rule_id: int):
    """Celery task to send Slack notifications for an alert group.

    Uses firing template by default; if the alert_group is resolved and the rule
    has a resolved_message_template, that template will be used instead.

    Channel resolution hierarchy:
      1) Rule-defined channel
      2) Alert label 'channel' (normalized)
      3) Default settings.SLACK_DEFAULT_CHANNEL or '#general'
    """
    try:
        alert_group = AlertGroup.objects.get(pk=alert_group_id)
        rule = SlackIntegrationRule.objects.get(pk=rule_id)
        fingerprint_for_log = alert_group.fingerprint
        logger.info(
            f"Slack Task {self.request.id} (FP: {fingerprint_for_log}): Starting for AlertGroup ID: {alert_group_id}, Rule ID: {rule_id}"
        )
    except AlertGroup.DoesNotExist:
        logger.error(f"Slack Task {self.request.id}: AlertGroup with ID {alert_group_id} not found. Aborting.")
        return
    except SlackIntegrationRule.DoesNotExist:
        logger.error(f"Slack Task {self.request.id}: SlackIntegrationRule with ID {rule_id} not found. Aborting.")
        return

    # --- START: Added Logic ---
    # Fetch the latest instance to get access to its annotations
    latest_instance = alert_group.instances.order_by('-started_at').first()
    annotations = latest_instance.annotations if latest_instance else {}
    summary = annotations.get('summary', alert_group.name)
    description = annotations.get('description', 'No description provided.')
    # --- END: Added Logic ---

    status = getattr(alert_group, "current_status", None)

    # --- MODIFIED: Updated Context ---
    context = {
        'alert_group': alert_group,
        'latest_instance': latest_instance,
        'annotations': annotations,
        'summary': summary,
        'description': description,
    }
    # --- END: Updated Context ---

    # Choose template based on status
    template_to_use = None
    if status == "resolved" and getattr(rule, "resolved_message_template", ""):
        template_to_use = rule.resolved_message_template
    else:
        template_to_use = rule.message_template

    message = render_template_safe(template_to_use or "", context, "")

    # If after rendering we still have empty message (e.g., no template provided), skip
    if not message:
        logger.info(
            f"Slack Task {self.request.id} (FP: {fingerprint_for_log}): No message to send for AlertGroup {alert_group_id} (status={status}). Skipping."
        )
        return

    # Resolve channel using matcher service (rule > label > default)
    from integrations.services.slack_matcher import SlackRuleMatcherService
    matcher = SlackRuleMatcherService()
    channel, source = matcher.resolve_channel(alert_group, rule)
    logger.info(
        f"Slack Task {self.request.id} (FP: {fingerprint_for_log}): Using channel {channel!r} resolved from {source} for AlertGroup {alert_group_id}."
    )

    slack_service = SlackService()
    try:
        slack_service.send_notification(channel, message)
        logger.info(
            f"Slack Task {self.request.id} (FP: {fingerprint_for_log}): Notification sent to {channel} for AlertGroup {alert_group_id}."
        )
    except SlackNotificationError as e:
        metrics_manager.increment("sentryhub_slack_notifications_total", {"status": "retry"})
        logger.warning(
            f"Slack Task {self.request.id} (FP: {fingerprint_for_log}): Network error when sending notification for AlertGroup {alert_group_id}. Retrying...",
            exc_info=True
        )
        raise self.retry(exc=e)
