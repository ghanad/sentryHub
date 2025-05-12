import logging
import json
from celery import shared_task
from django.db import transaction

from .services.payload_parser import parse_alertmanager_payload
from .services.alert_state_manager import update_alert_state
from .signals import alert_processed

logger = logging.getLogger(__name__)

# Note: The @shared_task decorator is kept, but the function will be called directly for this test.
# The 'bind=True' and 'self' argument are ignored in a direct call.
@shared_task(bind=True)
def process_alert_payload_task(self, payload_json: str): # Expect a JSON string now
    # --- Deserialize the incoming JSON string ---
    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to deserialize payload JSON: {e}", exc_info=True)
        # Decide how to handle this - maybe return or raise to stop processing
        return # Stop processing if JSON is invalid
    # --- End deserialization ---

    # In a direct call, 'self' will be None unless explicitly passed,
    # so we avoid using self.request.id here.
    logger.info(f"ENTERING process_alert_payload_task") # Removed (Direct Call Test) suffix
    
    # Removed json.loads() as we now expect a dict directly
        
    # Removed print statement, use logging instead.
    """
    Celery task to process Alertmanager payload.
    
    Args:
        payload: Raw Alertmanager webhook payload as a dictionary
        
    Returns:
        None
    """
    # --- Original Task Body (Using the 'payload' dict) ---
    try:
        logger.info("Task started execution (Direct Call Test)")
        logger.info(f"Received payload keys: {payload.keys()}") # Use the dict

        
        with transaction.atomic():
            # Pass the deserialized dictionary to the parser
            alerts = parse_alertmanager_payload(payload)
            logger.info(f"Parsed {len(alerts)} alerts from payload.")
            
            if not alerts:
                logger.warning("Payload parsed into zero alerts. No further processing.")
                return "Parsed zero alerts" # Return status for direct call

            for alert_data in alerts:
                alert_name = alert_data.get('labels', {}).get('alertname', 'N/A')
                fingerprint = alert_data.get('fingerprint', 'N/A')
                logger.info(f"Task {self.request.id if hasattr(self, 'request') else 'N/A_REQ'} (FP: {fingerprint}): Processing alert payload. Alertname: {alert_name}")
                
                # Update alert state in database
                alert_group, alert_instance = update_alert_state(alert_data)
                
                if alert_group and alert_instance:
                    group_id = getattr(alert_group, 'id', 'N/A')
                    instance_id = getattr(alert_instance, 'id', 'N/A')
                    logger.info(f"Successfully processed alert. AlertGroup ID: {group_id}, AlertInstance ID: {instance_id}")
                    logger.info(f"Task {self.request.id if hasattr(self, 'request') else 'N/A_REQ'} (FP: {alert_group.fingerprint}): Dispatching 'alert_processed' signal. AlertGroup ID: {alert_group.id}, Status: {alert_group.current_status}")
                    # Send signal after processing alert
                    alert_processed.send(
                        sender=alert_group.__class__,
                        alert_group=alert_group,
                        instance=alert_instance,
                        status=alert_group.current_status
                    )
                else:
                    logger.info(f"update_alert_state returned None for alert: Name='{alert_name}', Fingerprint='{fingerprint}'. No DB changes made (e.g., duplicate or error within update_alert_state).") 
            
            return "Processed alerts successfully (Direct Call)" # Return status

    except Exception as e:
        logger.error(f"Task failed during direct call: {str(e)}", exc_info=True)
        # Re-raise the exception so the calling view can catch it
        raise e 
    # --- End Original Task Body ---