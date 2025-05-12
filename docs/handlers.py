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
        # Add check for alert_group and extract fingerprint
        if not alert_group:
            logger.warning("Docs Handler: Received alert_processed signal without alert_group.")
            return
        fingerprint_for_log = alert_group.fingerprint
        status_kwarg = kwargs.get('status') # Get status for context
        logger.info(f"Docs Handler (FP: {fingerprint_for_log}): Received 'alert_processed'. Status: {status_kwarg}. Checking for documentation.")

        matched_doc = match_documentation_to_alert(alert_group)
        if matched_doc:
            logger.info(f"Docs Handler (FP: {fingerprint_for_log}): Matched documentation '{matched_doc.title}' (ID: {matched_doc.id}) for alert: {alert_group.name}")
        else:
            logger.info(f"Docs Handler (FP: {fingerprint_for_log}): No specific documentation found matching title for alert: {alert_group.name}")

    except Exception as e:
        # Ensure fingerprint is available for error logging if alert_group exists
        fingerprint_for_log = getattr(alert_group, 'fingerprint', 'N/A_FP') if 'alert_group' in locals() else 'N/A_FP'
        group_id = getattr(alert_group, 'id', 'N/A') if 'alert_group' in locals() else 'N/A'
        logger.error(f"Docs Handler (FP: {fingerprint_for_log}): Failed to match documentation for alert {group_id}: {str(e)}", exc_info=True)