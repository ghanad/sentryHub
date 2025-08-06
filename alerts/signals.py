import logging
from django.dispatch import Signal, receiver
from django.db.models.signals import post_save, post_delete
from django.db import transaction
from django.urls import reverse

from .models import SilenceRule, AlertGroup, AlertInstance
# Import the matcher function
from .services.silence_matcher import check_alert_silence

logger = logging.getLogger(__name__)

# Define a signal that will be sent when an alert is processed
alert_processed = Signal()


# --- Silence Rule Signal Handlers ---

def _rescan_alerts_for_silence(rule_instance=None):
    """
    Iterates through potentially affected alerts and re-checks their silence status.
    If rule_instance is provided (e.g., on delete), it might be used for optimization later,
    but for now, we rescan all active/unacknowledged alerts for simplicity.
    """
    logger.info(f"Silence rule change detected (Rule ID: {getattr(rule_instance, 'id', 'N/A')}). Rescanning alerts...")
    # Consider filtering alerts for efficiency, e.g., only 'firing' or recently active ones.
    # For robustness, let's check all non-resolved alerts for now.
    alerts_to_check = AlertGroup.objects.exclude(current_status='resolved')
    count = 0
    # Use transaction.atomic to ensure consistency if many alerts are updated
    with transaction.atomic():
        for alert_group in alerts_to_check.iterator(): # Use iterator for large querysets
            try:
                # check_alert_silence handles saving the alert_group if status changes
                check_alert_silence(alert_group)
                count += 1
            except Exception as e:
                logger.error(f"Error re-checking silence for AlertGroup {alert_group.id} ({alert_group.name}): {e}", exc_info=True)
    logger.info(f"Finished rescanning {count} alerts for silence status.")


@receiver(post_save, sender=SilenceRule)
def handle_silence_rule_save(sender, instance, created, **kwargs):
    """
    When a SilenceRule is created or updated, re-evaluate all relevant alerts.
    """
    logger.debug(f"post_save signal received for SilenceRule {instance.id}")
    _rescan_alerts_for_silence(instance)


@receiver(post_delete, sender=SilenceRule)
def handle_silence_rule_delete(sender, instance, **kwargs):
    """
    When a SilenceRule is deleted, re-evaluate all relevant alerts.
    The deleted rule won't be found by check_alert_silence, effectively unsilencing alerts
    that were only silenced by this rule.
    """
    logger.debug(f"post_delete signal received for SilenceRule {instance.id}")
    _rescan_alerts_for_silence(instance)

# --- End Silence Rule Signal Handlers ---

# --- Realtime broadcast on AlertInstance create ---

def _serialize_realtime_event(instance: AlertInstance) -> dict:
    """
    Build the payload for realtime stream.
    Fields: id, group_id, time, severity, source, message, environment, acknowledged, detail_url
    """
    g = instance.alert_group
    # Derive environment from labels if present
    environment = None
    try:
        environment = g.labels.get('environment') or g.labels.get('env') or ''
    except Exception:
        environment = ''
    message = ''
    try:
        message = instance.annotations.get('summary') or instance.annotations.get('description') or g.name
    except Exception:
        message = g.name

    detail_url = reverse('alerts:alert-detail', args=[g.id]) if _has_alert_detail_url() else '#'

    return {
        "id": instance.id,
        "group_id": g.id,
        "time": instance.started_at.isoformat() if instance.started_at else '',
        "severity": g.severity,
        "source": g.source or '',
        "message": message,
        "environment": environment,
        "acknowledged": g.acknowledged,
        "detail_url": detail_url,
    }


def _has_alert_detail_url() -> bool:
    """
    Check if alert detail URL name exists.
    """
    try:
        reverse('alerts:alert-detail', args=[1])
        return True
    except Exception:
        return False


@receiver(post_save, sender=AlertInstance)
def broadcast_realtime_on_instance_create(sender, instance: AlertInstance, created, **kwargs):
    """
    When a new AlertInstance is created for an unacknowledged AlertGroup that is firing and not silenced,
    broadcast a realtime event via Channels group.
    """
    if not created:
        return
    g = instance.alert_group
    if g.current_status != 'firing':
        return
    if g.acknowledged:
        return
    if g.is_silenced:
        return

    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()
        if channel_layer is None:
            logger.warning("Channel layer is not configured; skipping realtime broadcast")
            return

        payload = _serialize_realtime_event(instance)
        async_to_sync(channel_layer.group_send)(
            "alerts_stream",
            {
                "type": "alert.event",
                "payload": payload,
            },
        )
        logger.debug(f"Broadcasted realtime alert event for AlertInstance {instance.id}")
    except Exception as e:
        logger.error(f"Failed to broadcast realtime event for AlertInstance {instance.id}: {e}", exc_info=True)