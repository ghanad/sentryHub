# integrations/handlers.py

import logging
from django.dispatch import receiver
from alerts.signals import alert_processed
# Import AlertGroup if needed for type hinting or direct access, though it comes from kwargs
# from alerts.models import AlertGroup
from .services.jira_matcher import JiraRuleMatcherService
from integrations.tasks import process_jira_for_alert_group

logger = logging.getLogger(__name__)

@receiver(alert_processed)
def handle_alert_processed(sender, **kwargs):
    """
    Handles the alert_processed signal.
    Checks for matching Jira rules for firing alerts (not silenced)
    and for resolved alerts that already have an associated Jira issue key.
    Triggers the Jira processing task if a rule matches.
    """
    alert_group = kwargs.get('alert_group')
    status = kwargs.get('status')
    is_silenced = kwargs.get('is_silenced', False) # Default to False if not provided

    if not alert_group:
        logger.warning("Integrations Handler: Received alert_processed signal without alert_group. Cannot process for Jira.")
        return

    fingerprint_for_log = alert_group.fingerprint # Extract fingerprint
    status_kwarg = kwargs.get('status') # Renamed from status to avoid conflict
    is_silenced = kwargs.get('is_silenced', False) # Default to False if not provided

    logger.info(f"Integrations Handler (FP: {fingerprint_for_log}): Received 'alert_processed'. Status: {status_kwarg}. Current alert_group.is_silenced: {alert_group.is_silenced}")

    is_firing = (status_kwarg == 'firing')
    is_resolved = (status_kwarg == 'resolved')
    # fingerprint = alert_group.fingerprint # For logging - now using fingerprint_for_log

    # Determine if we should even look for a Jira rule
    # Condition:
    # 1. It's a 'firing' alert AND it's not silenced.
    # OR
    # 2. It's a 'resolved' alert AND the alert group already has a Jira issue key associated with it.
    should_find_rule = (is_firing and not is_silenced) or \
                       (is_resolved and alert_group.jira_issue_key)

    if should_find_rule:
        logger.info(f"Integrations Handler (FP: {fingerprint_for_log}): Checking Jira rules. Status: {status_kwarg}, Silenced: {is_silenced}")
        jira_matcher_service = JiraRuleMatcherService()
        # Use alert group labels to find the rule (consistent for firing/resolved)
        matching_rule = jira_matcher_service.find_matching_rule(alert_group.labels)

        if matching_rule:
            # We found a rule, now trigger the task.
            # The task itself will handle the logic based on the status ('firing' or 'resolved')
            # and the state of the Jira issue (open/closed).
            logger.info(f"Integrations Handler (FP: {fingerprint_for_log}): Matched Jira rule '{matching_rule.name}'. Triggering Jira task for status '{status_kwarg}'.")
            try:
                process_jira_for_alert_group.delay(
                    alert_group_id=alert_group.id,
                    rule_id=matching_rule.id,
                    alert_status=status # Pass the actual status ('firing' or 'resolved')
                )
            except Exception as e:
                logger.error(f"Integrations Handler (FP: {fingerprint_for_log}): Failed to queue Jira processing task for AlertGroup {alert_group.id}, status {status_kwarg}: {e}", exc_info=True)
        else:
            logger.info(f"Integrations Handler (FP: {fingerprint_for_log}): No matching Jira rule found. Status: {status_kwarg}, Silenced: {is_silenced}")
    else:
        # Log why we didn't check for rules
        reason = "alert is silenced" if is_silenced else \
                 "resolved alert has no existing Jira key" if is_resolved else \
                 f"alert status is '{status_kwarg}'"
        logger.info(f"Integrations Handler (FP: {fingerprint_for_log}): Not checking Jira rules because {reason}.")