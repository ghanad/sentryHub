import logging
from django.dispatch import receiver

from .signals import alert_processed
from .services.silence_matcher import check_alert_silence

logger = logging.getLogger(__name__)

@receiver(alert_processed)
def handle_silence_check(sender, alert_group, instance, status, **kwargs):
    """
    Signal receiver to check and apply silence rules for processed alerts.
    """
    try:
        is_silenced = check_alert_silence(alert_group)
        if is_silenced and status == 'firing':
            logger.info(f"Alert {alert_group.name} (Group ID: {alert_group.id}) is firing but currently silenced.")
        elif not is_silenced and alert_group.is_silenced:
            logger.info(f"Alert {alert_group.name} (Group ID: {alert_group.id}) was silenced but is no longer.")
    except Exception as e:
        logger.error(f"Failed to check silence for alert {alert_group.id}: {str(e)}")