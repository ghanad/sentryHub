from django.utils import timezone
from dateutil.parser import parse as parse_datetime
import re
import logging
import json

from ..models import AlertGroup, AlertInstance
from docs.services.documentation_matcher import match_documentation_to_alert

logger = logging.getLogger(__name__)

# alerts/services/alerts_processor.py - process_alert function with changes

def process_alert(alert_data):
    """
    Process an alert from Alertmanager.
    
    Args:
        alert_data (dict): Alert data from Alertmanager
        
    Returns:
        AlertGroup: The created or updated alert group
    """
    fingerprint = alert_data.get('fingerprint')
    status = alert_data.get('status')
    labels = alert_data.get('labels', {})
    annotations = alert_data.get('annotations', {})
    starts_at = parse_datetime(alert_data.get('startsAt'))
    ends_at = parse_datetime(alert_data.get('endsAt')) if alert_data.get('endsAt') and alert_data.get('endsAt') != '0001-01-01T00:00:00Z' else None
    generator_url = alert_data.get('generatorURL')
    
    logger.info(f"Processing alert: {labels.get('alertname')} - {fingerprint} - {status}")
    
    # Check if AlertGroup with this fingerprint exists
    alert_group, created = AlertGroup.objects.get_or_create(
        fingerprint=fingerprint,
        defaults={
            'name': labels.get('alertname', 'Unknown Alert'),
            'labels': labels,
            'severity': labels.get('severity', 'warning'),
            'current_status': status,
        }
    )
    
    if not created:
        # Update existing AlertGroup
        alert_group.current_status = status
        alert_group.last_occurrence = timezone.now()
        if status == 'firing' and alert_group.current_status != 'firing':
            alert_group.total_firing_count += 1
        alert_group.save()
    
    # Process based on status
    if status == 'firing':
        # Check for existing duplicate firing instances
        existing_firing = AlertInstance.objects.filter(
            alert_group=alert_group,
            status='firing',
            started_at=starts_at,
            ended_at__isnull=True
        ).exists()
        
        if existing_firing:
            logger.info(f"Skipping duplicate firing instance: {labels.get('alertname')} - {fingerprint}")
            return alert_group
        
        # Check if there's an active firing instance
        active_instance = AlertInstance.objects.filter(
            alert_group=alert_group,
            status='firing',
            ended_at__isnull=True
        ).first()
        
        if active_instance and active_instance.started_at != starts_at:
            # If the start times differ, close the old instance but mark it as inferred resolution
            active_instance.status = 'resolved'
            active_instance.resolution_type = 'inferred'
            # We set ended_at to null or we could also set it to current time
            # active_instance.ended_at = timezone.now()
            active_instance.ended_at = None
            active_instance.save()
            logger.info(f"Closed previous firing instance with inferred resolution (no explicit resolve received)")
        
        # Create new firing instance only if we don't have one with matching start time
        if not active_instance or active_instance.started_at != starts_at:
            new_instance = AlertInstance.objects.create(
                alert_group=alert_group,
                status=status,
                started_at=starts_at,
                ended_at=None,
                annotations=annotations,
                generator_url=generator_url,
                resolution_type=None  # No resolution for new firing alerts
            )
            logger.info(f"Created new firing instance (ID: {new_instance.id})")
    
    else:  # status is 'resolved'
        # Check if there's already a matching resolved instance
        existing_resolved = AlertInstance.objects.filter(
            alert_group=alert_group,
            status='resolved',
            started_at=starts_at,
            ended_at=ends_at or starts_at
        ).exists()
        
        if existing_resolved:
            logger.info(f"Skipping duplicate resolved instance: {labels.get('alertname')} - {fingerprint}")
            return alert_group
        
        # Find matching firing instance that started at the same time
        matching_firing = AlertInstance.objects.filter(
            alert_group=alert_group,
            status='firing',
            started_at=starts_at
        ).first()
        
        if matching_firing:
            # Update the existing firing instance to resolved instead of creating a new one
            matching_firing.status = 'resolved'
            matching_firing.ended_at = ends_at or starts_at
            matching_firing.resolution_type = 'normal'  # This is a normal resolution from Alertmanager
            matching_firing.save()
            logger.info(f"Updated firing instance to resolved status (ID: {matching_firing.id})")
        else:
            # Find any active firing instances to close
            active_instances = AlertInstance.objects.filter(
                alert_group=alert_group,
                status='firing',
                ended_at__isnull=True
            )
            
            if active_instances.exists():
                # Close all active instances with resolved time
                for instance in active_instances:
                    instance.status = 'resolved'
                    instance.ended_at = ends_at or starts_at
                    instance.resolution_type = 'normal'
                    instance.save()
                logger.info(f"Closed {active_instances.count()} active firing instances with normal resolution")
            
            # Create a new resolved instance only if we didn't find and update a matching firing instance
            new_instance = AlertInstance.objects.create(
                alert_group=alert_group,
                status=status,
                started_at=starts_at,
                ended_at=ends_at or starts_at,
                annotations=annotations,
                generator_url=generator_url,
                resolution_type='normal'  # This is a normal resolution
            )
            logger.info(f"Created new resolved instance (ID: {new_instance.id})")
    
    # Try to match documentation to this alert
    matched_doc = match_documentation_to_alert(alert_group)
    if matched_doc:
        logger.info(f"Documentation '{matched_doc.title}' automatically linked to alert '{alert_group.name}'")
    else:
        logger.info(f"No matching documentation found for alert '{alert_group.name}'")
    
    return alert_group


def acknowledge_alert(alert_group, user):
    """
    Acknowledge an alert.
    
    Args:
        alert_group (AlertGroup): The alert group to acknowledge
        user (User): The user who acknowledged the alert
        
    Returns:
        AlertGroup: The updated alert group
    """
    alert_group.acknowledged = True
    alert_group.acknowledged_by = user
    alert_group.acknowledgement_time = timezone.now()
    alert_group.save()
    
    return alert_group