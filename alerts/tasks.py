import logging
from celery import shared_task
from django.db import transaction

from .services.payload_parser import parse_alertmanager_payload
from .services.alert_state_manager import update_alert_state
from .signals import alert_processed

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def process_alert_payload_task(self, payload: dict):
    """
    Celery task to process Alertmanager payload.
    
    Args:
        payload: Raw Alertmanager webhook payload
        
    Returns:
        None
    """
    try:
        logger.info("Task started execution")  # Initial log
        logger.info(f"Payload keys: {payload.keys()}")  # Log payload structure
        
        with transaction.atomic():
            # Parse payload into standardized alerts
            alerts = parse_alertmanager_payload(payload)
            logger.info(f"Parsed {len(alerts)} alerts from payload")
            
            for alert_data in alerts:
                logger.info(f"Processing alert: {alert_data.get('labels', {}).get('alertname')}")
                
                # Update alert state in database
                alert_group, alert_instance = update_alert_state(alert_data)
                
                if alert_group and alert_instance:
                    logger.info(f"Successfully processed alert {alert_group.id}")
                    # Send signal after processing alert
                    alert_processed.send(
                        sender=alert_group.__class__,
                        alert_group=alert_group,
                        instance=alert_instance,
                        status=alert_group.current_status
                    )
                else:
                    logger.error("Failed to process alert - returned None")
                    
    except Exception as e:
        logger.error(f"Task failed: {str(e)}", exc_info=True)
        raise self.retry(exc=e)