# File: alerts/tasks.py
import logging
import json
from celery import shared_task
from django.db import transaction
from django.conf import settings
from core.services.metrics import metrics_manager
from .services.payload_parser import parse_alertmanager_payload
from .services.alert_state_manager import update_alert_state
from .signals import alert_processed

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def process_alert_payload_task(self, payload_json: str):
    """
    Celery task to process Alertmanager payload.
    It deserializes the payload, parses it, updates the database,
    and emits signals and metrics.
    """
    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to deserialize payload JSON: {e}", exc_info=True)
        return

    logger.info(f"ENTERING process_alert_payload_task for payload from externalURL: {payload.get('externalURL', 'N/A')}")

    try:
        with transaction.atomic():
            alerts = parse_alertmanager_payload(payload)
            logger.info(f"Parsed {len(alerts)} alerts from payload.")

            if not alerts:
                logger.warning("Payload parsed into zero alerts. No further processing.")
                return "Parsed zero alerts"

            for alert_data in alerts:
                status_metric = alert_data.get('status', 'unknown')
                source_metric = alert_data.get('source') or 'unknown' 

                if settings.METRICS_ENABLED:
                    metrics_manager.inc_counter(
                        'sentryhub_alerts_received_total',
                        labels={'status': status_metric, 'source': source_metric}
                    )
                    logger.debug(f"Incremented sentryhub_alerts_received_total for status='{status_metric}', source='{source_metric}'")

                alert_name = alert_data.get('labels', {}).get('alertname', 'N/A')
                fingerprint = alert_data.get('fingerprint', 'N/A')
                logger.info(f"Task {self.request.id if hasattr(self, 'request') else 'N/A_REQ'} (FP: {fingerprint}): Processing alert payload. Alertname: {alert_name}")

                alert_group, alert_instance = update_alert_state(alert_data)

                if alert_group and alert_instance:
                    group_id = getattr(alert_group, 'id', 'N/A')
                    instance_id = getattr(alert_instance, 'id', 'N/A')
                    logger.info(f"Successfully processed alert. AlertGroup ID: {group_id}, AlertInstance ID: {instance_id}")
                    logger.info(f"Task {self.request.id if hasattr(self, 'request') else 'N/A_REQ'} (FP: {alert_group.fingerprint}): Dispatching 'alert_processed' signal. AlertGroup ID: {alert_group.id}, Status: {alert_group.current_status}")
                    alert_processed.send(
                        sender=alert_group.__class__,
                        alert_group=alert_group,
                        instance=alert_instance,
                        status=alert_group.current_status
                    )
                else:
                    logger.info(f"update_alert_state returned None for alert: Name='{alert_name}', Fingerprint='{fingerprint}'. No DB changes made (e.g., duplicate or error within update_alert_state).")

            return "Processed alerts successfully"

    except Exception as e:
        logger.error(f"Task failed during direct call: {str(e)}", exc_info=True)
        # Re-raise the exception so the calling view can catch it and Celery can retry
        raise e