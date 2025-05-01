from django.utils import timezone
import logging

from ..models import AlertGroup, AlertInstance, AlertAcknowledgementHistory

logger = logging.getLogger(__name__)

def acknowledge_alert(alert_group, user, comment=None):
    """Acknowledge an alert."""
    alert_group.acknowledged = True
    alert_group.acknowledged_by = user
    alert_group.acknowledgement_time = timezone.now()
    alert_group.save(update_fields=['acknowledged', 'acknowledged_by', 'acknowledgement_time'])

    active_instance = get_active_firing_instance(alert_group)
    AlertAcknowledgementHistory.objects.create(
        alert_group=alert_group,
        alert_instance=active_instance,
        acknowledged_by=user,
        comment=comment
    )

    # Add logging after saving and creating history
    logger.info(f"Alert acknowledged: '{alert_group.name}' (FP: {alert_group.fingerprint}) by user '{user.username}'")

    return alert_group

def get_active_firing_instance(alert_group):
    """Get the active firing instance for an alert group."""
    return AlertInstance.objects.filter(
        alert_group=alert_group,
        status='firing',
        ended_at__isnull=True
    ).first()
