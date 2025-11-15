from django.utils import timezone
from django.db import transaction
import logging

from ..models import AlertGroup, AlertInstance, AlertAcknowledgementHistory, AlertComment

logger = logging.getLogger(__name__)


class ManualResolutionError(Exception):
    """Raised when a manual resolution cannot be applied."""


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


def manually_resolve_alert(alert_group, user, resolved_at, note=None):
    """Resolve the currently firing alert instance manually."""
    with transaction.atomic():
        active_instances = AlertInstance.objects.select_for_update().filter(
            alert_group=alert_group,
            status='firing',
            ended_at__isnull=True
        ).order_by('-started_at')

        if not active_instances.exists():
            raise ManualResolutionError('No active firing instances found to resolve.')

        primary_instance = active_instances.first()
        if resolved_at < primary_instance.started_at:
            raise ManualResolutionError('Resolution time cannot be earlier than the alert start time.')

        for instance in active_instances:
            instance.status = 'resolved'
            instance.ended_at = resolved_at
            instance.resolution_type = 'manual'
            instance.save(update_fields=['status', 'ended_at', 'resolution_type'])

        AlertGroup.objects.filter(pk=alert_group.pk).update(
            current_status='resolved',
            last_occurrence=resolved_at,
        )
        alert_group.current_status = 'resolved'
        alert_group.last_occurrence = resolved_at

        if note:
            AlertComment.objects.create(
                alert_group=alert_group,
                user=user,
                content=f"Manual resolve: {note}"
            )

        logger.info(
            "Alert '%s' (FP: %s) manually resolved by %s at %s",
            alert_group.name,
            alert_group.fingerprint,
            user.username,
            resolved_at.isoformat()
        )

        return primary_instance

def get_active_firing_instance(alert_group):
    """Get the active firing instance for an alert group."""
    return AlertInstance.objects.filter(
        alert_group=alert_group,
        status='firing',
        ended_at__isnull=True
    ).first()
