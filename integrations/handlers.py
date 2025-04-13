import logging
from django.dispatch import receiver
from alerts.signals import alert_processed
from .services.jira_matcher import JiraRuleMatcherService
from integrations.tasks import process_jira_for_alert_group

logger = logging.getLogger(__name__)

@receiver(alert_processed)
def handle_alert_processed(sender, **kwargs):
    alert_group = kwargs.get('alert_group')
    status = kwargs.get('status')
    is_silenced = kwargs.get('is_silenced')
    
    # Only process firing alerts that aren't silenced
    if status == 'firing' and not is_silenced:
        logger.debug(f"Checking Jira rules for alert group {alert_group.fingerprint}")
        jira_matcher_service = JiraRuleMatcherService()
        matching_rule = jira_matcher_service.find_matching_rule(alert_group.labels)

        if matching_rule:
            logger.info(f"Alert group {alert_group.fingerprint} matched Jira rule '{matching_rule.name}'. Triggering Jira processing task.")
            try:
                process_jira_for_alert_group.delay(
                    alert_group_id=alert_group.id,
                    rule_id=matching_rule.id,
                    alert_status=status
                )
            except Exception as e:
                logger.error(f"Failed to queue Jira processing task for alert group {alert_group.id}: {e}", exc_info=True)