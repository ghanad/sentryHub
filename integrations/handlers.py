# integrations/handlers.py

import logging
from django.dispatch import receiver
from alerts.signals import alert_processed
# Import AlertGroup if needed for type hinting or direct access, though it comes from kwargs
from alerts.models import AlertGroup, AlertInstance # AlertInstance را اضافه کنید
from .services.jira_matcher import JiraRuleMatcherService
from .services.slack_matcher import SlackRuleMatcherService
from integrations.tasks import process_jira_for_alert_group, process_slack_for_alert_group

logger = logging.getLogger(__name__)

@receiver(alert_processed)
def handle_alert_processed(sender, **kwargs):
    """
    Handles the alert_processed signal.
    Checks for matching Jira rules for firing alerts (not silenced)
    and for resolved alerts that already have an associated Jira issue key.
    Triggers the Jira processing task if a rule matches, passing the specific instance.
    """
    alert_group = kwargs.get('alert_group')
    status = kwargs.get('status') # 'firing' or 'resolved'
    triggering_instance: AlertInstance = kwargs.get('instance')

    if not alert_group:
        logger.warning("Integrations Handler: Received alert_processed signal without alert_group. Cannot process for Jira.")
        return

    fingerprint_for_log = alert_group.fingerprint
    is_silenced = alert_group.is_silenced 

    logger.info(f"Integrations Handler (FP: {fingerprint_for_log}): Received 'alert_processed'. Status: {status}. AlertGroup is_silenced: {is_silenced}")

    is_firing = (status == 'firing')
    is_resolved = (status == 'resolved')

    should_find_rule = (is_firing and not is_silenced) or \
                       (is_resolved and alert_group.jira_issue_key)

    if should_find_rule:
        logger.info(f"Integrations Handler (FP: {fingerprint_for_log}): Checking Jira rules. Status: {status}, Silenced: {is_silenced}")
        jira_matcher_service = JiraRuleMatcherService()
        matching_rule = jira_matcher_service.find_matching_rule(alert_group.labels)

        if matching_rule:
            logger.info(f"Integrations Handler (FP: {fingerprint_for_log}): Matched Jira rule '{matching_rule.name}'. Triggering Jira task for status '{status}'.")
            try:
                process_jira_for_alert_group.delay(
                    alert_group_id=alert_group.id,
                    rule_id=matching_rule.id,
                    alert_status=status,
                    triggering_instance_id=triggering_instance.id if triggering_instance else None
                )
            except Exception as e:
                logger.error(f"Integrations Handler (FP: {fingerprint_for_log}): Failed to queue Jira processing task for AlertGroup {alert_group.id}, status {status}: {e}", exc_info=True)
        else:
            logger.info(f"Integrations Handler (FP: {fingerprint_for_log}): No matching Jira rule found. Status: {status}, Silenced: {is_silenced}")
    else:
        reason = "alert is silenced" if is_silenced else \
                 "resolved alert has no existing Jira key" if is_resolved else \
                 f"alert status is '{status}' (and not firing or not resolved with key)"
        logger.info(f"Integrations Handler (FP: {fingerprint_for_log}): Not checking Jira rules because {reason}.")


@receiver(alert_processed)
def handle_alert_processed_slack(sender, **kwargs):
    """Trigger Slack notifications for firing and resolved alerts (when rule is active) that are not silenced."""
    alert_group = kwargs.get('alert_group')
    status = kwargs.get('status')

    if not alert_group:
        logger.warning("Integrations Handler: Received alert_processed signal without alert_group. Cannot process for Slack.")
        return

    # Skip silenced alerts entirely
    if alert_group.is_silenced:
        return

    # Only act on firing or resolved
    if status not in ('firing', 'resolved'):
        return

    matcher = SlackRuleMatcherService()
    rule = matcher.find_matching_rule(alert_group)
    if rule and rule.is_active:
        try:
            process_slack_for_alert_group.delay(
                alert_group_id=alert_group.id,
                rule_id=rule.id,
            )
        except Exception as e:
            logger.error(
                f"Integrations Handler: Failed to queue Slack processing task for AlertGroup {alert_group.id}: {e}",
                exc_info=True,
            )