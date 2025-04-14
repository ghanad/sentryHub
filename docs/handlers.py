import logging
from django.dispatch import receiver

from alerts.signals import alert_processed
from .services.documentation_matcher import match_documentation_to_alert

logger = logging.getLogger(__name__)

@receiver(alert_processed)
def handle_documentation_matching(sender, alert_group, instance, status, **kwargs):
    """
    Signal receiver to match documentation to processed alerts.
    """
    try:
        matched_doc = match_documentation_to_alert(alert_group)
        if matched_doc:
            logger.info(f"Matched documentation for alert: {alert_group.name}")
    except Exception as e:
        logger.error(f"Failed to match documentation for alert {alert_group.id}: {str(e)}")