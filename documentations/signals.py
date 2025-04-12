from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import AlertDocumentation
from alerts.models import AlertGroup
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=AlertDocumentation)
def match_documentation_to_existing_alerts(sender, instance, created, **kwargs):
    """
    When a new documentation is created or updated, try to match it with existing alerts.
    """
    logger.info(f"Attempting to match documentation '{instance.title}' with existing alerts")
    matching_alerts = AlertGroup.objects.filter(name=instance.title)
    
    if matching_alerts.exists():
        logger.info(f"Found {matching_alerts.count()} matching alerts for documentation '{instance.title}'")
    else:
        logger.warning(f"No matching alerts found for documentation '{instance.title}'")
    
    for alert in matching_alerts:
        from docs.services.documentation_matcher import match_documentation_to_alert
        logger.info(f"Matching documentation with alert: {alert.name}")
        match_documentation_to_alert(alert)