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
        # Add check for alert_group and extract fingerprint
        if not alert_group:
            logger.warning("Alerts Handler (Silence Check): Received alert_processed signal without alert_group.")
            return
        fingerprint_for_log = alert_group.fingerprint
        logger.info(f"Alerts Handler (Silence Check) (FP: {fingerprint_for_log}): Received 'alert_processed'. Status: {status}. Checking silence rules.")

        is_silenced = check_alert_silence(alert_group)
        if is_silenced and status == 'firing':
            logger.info(f"Alerts Handler (Silence Check) (FP: {fingerprint_for_log}): Alert {alert_group.name} (Group ID: {alert_group.id}) is firing but currently silenced.")
        elif not is_silenced and alert_group.is_silenced:
            logger.info(f"Alerts Handler (Silence Check) (FP: {fingerprint_for_log}): Alert {alert_group.name} (Group ID: {alert_group.id}) was silenced but is no longer.")
    except Exception as e:
        # Ensure fingerprint is available for error logging if alert_group exists
        fingerprint_for_log = getattr(alert_group, 'fingerprint', 'N/A_FP') if 'alert_group' in locals() else 'N/A_FP'
        group_id = getattr(alert_group, 'id', 'N/A') if 'alert_group' in locals() else 'N/A'
        logger.error(f"Alerts Handler (Silence Check) (FP: {fingerprint_for_log}): Failed to check silence for alert {group_id}: {str(e)}")