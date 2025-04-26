import logging
import json
import re
from typing import Optional, Dict, Any

from celery import shared_task, Task
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.template import Context, Template, TemplateSyntaxError # Added for template rendering

from integrations.services.jira_service import JiraService
from integrations.models import JiraIntegrationRule
from alerts.models import AlertGroup, AlertInstance

logger = logging.getLogger(__name__)

# Base task with retry logic for API calls
class JiraTaskBase(Task):
    retry_kwargs = {'max_retries': 3, 'countdown': 15}
    retry_backoff = True
    retry_jitter = True

def render_template_safe(template_string: str, context_dict: Dict[str, Any]) -> str:
    """Safely renders a Django template string with given context."""
    if not template_string:
        return "" # Return empty string if template is empty
    try:
        template = Template(template_string)
        context = Context(context_dict)
        return template.render(context)
    except TemplateSyntaxError as e:
        logger.error(f"Template syntax error during rendering: {e}", exc_info=True)
        return f"Error rendering template: {e}" # Return error message
    except Exception as e:
        logger.error(f"Unexpected error during template rendering: {e}", exc_info=True)
        return f"Unexpected error rendering template: {e}"

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

    # --- Prepare context for template rendering ---
    try:
        sentryhub_url_path = reverse('alerts:alert_detail', args=[alert_group.fingerprint])
        full_sentryhub_url = f"{settings.SITE_URL.strip('/')}{sentryhub_url_path}"
    except Exception:
        full_sentryhub_url = "N/A (Check SITE_URL setting and URL config)"

    template_context = {
        'alert_group': alert_group,
        'labels': alert_group.labels,
        'annotations': latest_instance.annotations if latest_instance else {},
        'status': alert_status,
        'fingerprint': alert_group.fingerprint,
        'alertname': alert_group.get_common_label('alertname', 'N/A'),
        'severity': alert_group.get_common_label('severity', 'default'),
        'instance_summary': latest_instance.summary if latest_instance else 'N/A',
        'instance_description': latest_instance.description if latest_instance else 'N/A',
        'rule': rule,
        'sentryhub_url': full_sentryhub_url,
        'now': timezone.now(),
        # Add any other relevant context variables here
    }
    # --- End context preparation ---

    try:
        if alert_status == 'firing':
            if existing_issue_key:
                if issue_status_category in open_categories:
                    # Render update comment template
                    comment_body = render_template_safe(rule.jira_update_comment_template, template_context)
                    if comment_body: # Only add comment if template rendered something
                        logger.info(f"Task {self.request.id}: Adding 'firing again' comment (rendered) to open Jira issue: {existing_issue_key}")
                        success = jira_service.add_comment(existing_issue_key, comment_body)
                        if not success: raise Exception(f"Failed to add comment to {existing_issue_key}")
                    else:
                        logger.info(f"Task {self.request.id}: Jira update comment template for rule {rule.id} is empty or failed to render. Skipping comment.")
                elif issue_status_category in closed_categories:
                    logger.info(f"Task {self.request.id}: Existing Jira issue {existing_issue_key} is closed. Creating new issue.")
                    alert_group.jira_issue_key = None
                    alert_group.save(update_fields=['jira_issue_key'])
                else: # Issue exists but status is neither open nor closed (e.g., 'Undefined')
                    logger.warning(f"Task {self.request.id}: Jira issue {existing_issue_key} has status category '{issue_status_category}'. Adding comment based on template.")
                    # Render update comment template
                    comment_body = render_template_safe(rule.jira_update_comment_template, template_context)
                    if comment_body:
                        success = jira_service.add_comment(existing_issue_key, comment_body)
                        if not success: raise Exception(f"Failed to add comment to {existing_issue_key}")
                    else:
                         logger.info(f"Task {self.request.id}: Jira update comment template for rule {rule.id} is empty or failed to render. Skipping comment.")

            # --- Create new issue if needed ---
            if not alert_group.jira_issue_key:
                # Render title and description from templates
                rendered_summary = render_template_safe(rule.jira_title_template, template_context)
                rendered_description = render_template_safe(rule.jira_description_template, template_context)

                # Fallback if templates are empty or fail
                if not rendered_summary:
                    severity = alert_group.get_common_label('severity', 'default').capitalize()
                    rendered_summary = f"[{severity}] SentryHub Alert: {template_context['instance_summary']}"[:250]
                    logger.warning(f"Task {self.request.id}: Jira title template for rule {rule.id} was empty or failed to render. Using default summary.")
                if not rendered_description:
                    # Use original logic as fallback for description
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
                        json.dumps(template_context['annotations'], indent=2),
                        "{code}",
                        f"\n*Latest Alert Summary:* {template_context['instance_summary']}",
                        f"*Latest Alert Description:* {template_context['instance_description']}",
                        f"\n[Link to SentryHub|{full_sentryhub_url}]"
                    ]
                    rendered_description = "\n".join(description_parts)
                    logger.warning(f"Task {self.request.id}: Jira description template for rule {rule.id} was empty or failed to render. Using default description.")

                logger.info(f"Task {self.request.id}: Creating new Jira issue for alert group {alert_group_id} in project {rule.jira_project_key} using rendered templates.")
                # Prepare Jira labels (keep existing logic)
                jira_labels = ['sentryhub', alert_group.get_common_label('severity', 'default')]
                for key, value in alert_group.labels.items():
                    sanitized_label = re.sub(r'[^\w-]+', '_', f"{key}_{value}")[:255]
                    if len(sanitized_label) > 0:
                        jira_labels.append(sanitized_label)

                extra_fields = {'labels': list(set(jira_labels))}

                new_issue_key = jira_service.create_issue(
                    project_key=rule.jira_project_key,
                    issue_type=rule.jira_issue_type,
                    summary=rendered_summary.strip()[:255], # Ensure summary length limit
                    description=rendered_description.strip(),
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
                # Render update comment template for resolved status
                comment_body = render_template_safe(rule.jira_update_comment_template, template_context)
                if comment_body:
                    logger.info(f"Task {self.request.id}: Adding 'resolved' comment (rendered) to open Jira issue: {existing_issue_key}")
                    success = jira_service.add_comment(existing_issue_key, comment_body)
                    if not success: raise Exception(f"Failed to add resolved comment to {existing_issue_key}")
                else:
                    logger.info(f"Task {self.request.id}: Jira update comment template for rule {rule.id} is empty or failed to render. Skipping resolved comment.")
            elif existing_issue_key:
                logger.info(f"Task {self.request.id}: Alert group {alert_group_id} resolved, but Jira issue {existing_issue_key} has status '{issue_status_category}'. No comment added.")
            else:
                logger.info(f"Task {self.request.id}: Alert group {alert_group_id} resolved, but no associated Jira issue found. No action taken.")

    except Exception as e:
        logger.error(f"Task {self.request.id}: An error occurred during Jira processing for AlertGroup {alert_group_id}: {e}", exc_info=True)
        raise e # Re-raise the exception to mark the task as failed immediately

    logger.info(f"Finished Jira processing task {self.request.id} for AlertGroup ID: {alert_group_id}")