from django.utils import timezone
from dateutil.parser import parse as parse_datetime
import re
import logging
import json

from ..models import AlertGroup, AlertInstance, AlertAcknowledgementHistory, SilenceRule # SilenceRule might not be needed directly, but good for context
from docs.services.documentation_matcher import match_documentation_to_alert
from .silence_matcher import check_alert_silence # Import the new function


logger = logging.getLogger(__name__)


def process_alert(alert_data):
    """
    Process an alert from Alertmanager.
    
    Args:
        alert_data (dict): Alert data from Alertmanager
        
    Returns:
        AlertGroup: The created or updated alert group
    """
    # Extract alert information
    fingerprint, status, labels, annotations, starts_at, ends_at, generator_url = extract_alert_data(alert_data)
    
    # Get or create alert group
    alert_group = get_or_create_alert_group(fingerprint, status, labels)

    # Check for silence *before* further processing or status updates might rely on it
    is_silenced = check_alert_silence(alert_group)
    if is_silenced and status == 'firing':
        logger.info(f"Alert {alert_group.name} (Group ID: {alert_group.id}) is firing but currently silenced until {alert_group.silenced_until}.")
    elif not is_silenced and alert_group.is_silenced: # This case should be handled by check_alert_silence saving the model
        logger.info(f"Alert {alert_group.name} (Group ID: {alert_group.id}) was silenced but is no longer.")


    # Process the alert
    if status == 'firing':
        process_firing_alert(alert_group, labels, fingerprint, starts_at, annotations, generator_url)
    else:  # status is 'resolved'
        process_resolved_alert(alert_group, labels, fingerprint, starts_at, ends_at, annotations, generator_url)
    
    # Try to find related documentation for this alert
    try_match_documentation(alert_group)
    
    return alert_group

def extract_alert_data(alert_data):
    """
    Extract relevant data from the alert.
    
    Args:
        alert_data (dict): Alert data from Alertmanager
        
    Returns:
        tuple: fingerprint, status, labels, annotations, starts_at, ends_at, generator_url
    """
    fingerprint = alert_data.get('fingerprint')
    status = alert_data.get('status')
    labels = alert_data.get('labels', {})
    annotations = alert_data.get('annotations', {})
    starts_at = parse_datetime(alert_data.get('startsAt'))
    ends_at = None
    if alert_data.get('endsAt') and alert_data.get('endsAt') != '0001-01-01T00:00:00Z':
        ends_at = parse_datetime(alert_data.get('endsAt'))
    generator_url = alert_data.get('generatorURL')
    
    logger.info(f"Processing alert: {labels.get('alertname')} - {fingerprint} - {status}")
    
    return fingerprint, status, labels, annotations, starts_at, ends_at, generator_url

def get_or_create_alert_group(fingerprint, status, labels):
    """
    Get or create an AlertGroup.
    
    Args:
        fingerprint (str): Alert fingerprint
        status (str): Alert status
        labels (dict): Alert labels
        
    Returns:
        AlertGroup: The created or updated alert group
    """
    instance = labels.get('instance')
    
    alert_group, created = AlertGroup.objects.get_or_create(
        fingerprint=fingerprint,
        defaults={
            'name': labels.get('alertname', 'Unknown Alert'),
            'labels': labels,
            'severity': labels.get('severity', 'warning'),
            'current_status': status,
            'instance': instance,
        }
    )
    
    if not created:
        # Update existing AlertGroup
        alert_group.current_status = status
        alert_group.last_occurrence = timezone.now()
        
        if instance and alert_group.instance != instance:
            alert_group.instance = instance
            
        if status == 'firing' and alert_group.current_status != 'firing':
            alert_group.total_firing_count += 1
        alert_group.save()
    
    return alert_group

def process_firing_alert(alert_group, labels, fingerprint, starts_at, annotations, generator_url):
    """
    Process a firing alert.
    
    Args:
        alert_group (AlertGroup): The alert group
        labels (dict): Alert labels
        fingerprint (str): Alert fingerprint
        starts_at (datetime): Alert start time
        annotations (dict): Alert annotations
        generator_url (str): Alert generator URL
    """
    # Check for existing duplicate firing instances
    if is_duplicate_firing(alert_group, starts_at):
        logger.info(f"Skipping duplicate firing instance: {labels.get('alertname')} - {fingerprint}")
        return
    
    # Check if there's an active firing instance
    active_instance = get_active_firing_instance(alert_group)
    
    # Reset acknowledgement if this is a new firing after a previous resolution
    # This only happens if there are no active firing instances or if this is a new firing with a different start time
    if (not active_instance) or (active_instance and active_instance.started_at != starts_at):
        if alert_group.acknowledged:
            # Reset acknowledgement state
            alert_group.acknowledged = False
            alert_group.acknowledged_by = None
            alert_group.acknowledgement_time = None
            # Log this action
            logger.info(f"Reset acknowledgement for alert group: {alert_group.name} (ID: {alert_group.id}) due to new firing")
            alert_group.save()
    
    if active_instance and active_instance.started_at != starts_at:
        # If the start times differ, close the old instance but mark it as inferred resolution
        handle_inferred_resolution(active_instance)
    
    # Create new firing instance only if we don't have one with matching start time
    if not active_instance or active_instance.started_at != starts_at:
        create_new_firing_instance(alert_group, starts_at, annotations, generator_url)

def is_duplicate_firing(alert_group, starts_at):
    """
    Check if the firing alert is a duplicate.
    
    Args:
        alert_group (AlertGroup): The alert group
        starts_at (datetime): Alert start time
        
    Returns:
        bool: True if it's a duplicate, False otherwise
    """
    return AlertInstance.objects.filter(
        alert_group=alert_group,
        status='firing',
        started_at=starts_at,
        ended_at__isnull=True
    ).exists()

def get_active_firing_instance(alert_group):
    """
    Get the active firing instance for an alert group.
    
    Args:
        alert_group (AlertGroup): The alert group
        
    Returns:
        AlertInstance: The active firing instance or None
    """
    return AlertInstance.objects.filter(
        alert_group=alert_group,
        status='firing',
        ended_at__isnull=True
    ).first()

def handle_inferred_resolution(active_instance):
    """
    Handle inferred resolution for an active instance.
    
    Args:
        active_instance (AlertInstance): The active instance to mark as resolved
    """
    active_instance.status = 'resolved'
    active_instance.resolution_type = 'inferred'
    active_instance.ended_at = None
    active_instance.save()
    logger.info(f"Closed previous firing instance with inferred resolution (no explicit resolve received)")

def create_new_firing_instance(alert_group, starts_at, annotations, generator_url):
    """
    Create a new firing instance.
    
    Args:
        alert_group (AlertGroup): The alert group
        starts_at (datetime): Alert start time
        annotations (dict): Alert annotations
        generator_url (str): Alert generator URL
        
    Returns:
        AlertInstance: The created instance
    """
    new_instance = AlertInstance.objects.create(
        alert_group=alert_group,
        status='firing',
        started_at=starts_at,
        ended_at=None,
        annotations=annotations,
        generator_url=generator_url,
        resolution_type=None  # No resolution for new firing alerts
    )
    logger.info(f"Created new firing instance (ID: {new_instance.id})")
    return new_instance

def process_resolved_alert(alert_group, labels, fingerprint, starts_at, ends_at, annotations, generator_url):
    """
    Process a resolved alert.
    
    Args:
        alert_group (AlertGroup): The alert group
        labels (dict): Alert labels
        fingerprint (str): Alert fingerprint
        starts_at (datetime): Alert start time
        ends_at (datetime): Alert end time
        annotations (dict): Alert annotations
        generator_url (str): Alert generator URL
    """
    # Check if there's already a matching resolved instance
    if is_duplicate_resolved(alert_group, starts_at, ends_at):
        logger.info(f"Skipping duplicate resolved instance: {labels.get('alertname')} - {fingerprint}")
        return
    
    # Find matching firing instance that started at the same time
    matching_firing = get_matching_firing_instance(alert_group, starts_at)
    
    if matching_firing:
        # Update the existing firing instance to resolved instead of creating a new one
        update_to_resolved(matching_firing, ends_at or starts_at)
    else:
        # Find any active firing instances to close
        active_instances = get_all_active_firing_instances(alert_group)
        
        if active_instances.exists():
            # Close all active instances with resolved time
            resolve_all_active_instances(active_instances, ends_at or starts_at)
        
        # Create a new resolved instance only if we didn't find and update a matching firing instance
        create_new_resolved_instance(alert_group, starts_at, ends_at, annotations, generator_url)

def is_duplicate_resolved(alert_group, starts_at, ends_at):
    """
    Check if the resolved alert is a duplicate.
    
    Args:
        alert_group (AlertGroup): The alert group
        starts_at (datetime): Alert start time
        ends_at (datetime): Alert end time
        
    Returns:
        bool: True if it's a duplicate, False otherwise
    """
    return AlertInstance.objects.filter(
        alert_group=alert_group,
        status='resolved',
        started_at=starts_at,
        ended_at=ends_at or starts_at
    ).exists()

def get_matching_firing_instance(alert_group, starts_at):
    """
    Get a firing instance that matches the start time.
    
    Args:
        alert_group (AlertGroup): The alert group
        starts_at (datetime): Alert start time
        
    Returns:
        AlertInstance: The matching firing instance or None
    """
    return AlertInstance.objects.filter(
        alert_group=alert_group,
        status='firing',
        started_at=starts_at
    ).first()

def update_to_resolved(instance, end_time):
    """
    Update a firing instance to resolved status.
    
    Args:
        instance (AlertInstance): The instance to update
        end_time (datetime): The end time
    """
    instance.status = 'resolved'
    instance.ended_at = end_time
    instance.resolution_type = 'normal'
    instance.save()
    logger.info(f"Updated firing instance to resolved status (ID: {instance.id})")

def get_all_active_firing_instances(alert_group):
    """
    Get all active firing instances for an alert group.
    
    Args:
        alert_group (AlertGroup): The alert group
        
    Returns:
        QuerySet: Query set with all active firing instances
    """
    return AlertInstance.objects.filter(
        alert_group=alert_group,
        status='firing',
        ended_at__isnull=True
    )

def resolve_all_active_instances(active_instances, end_time):
    """
    Resolve all active instances.
    
    Args:
        active_instances (QuerySet): Active instances to resolve
        end_time (datetime): The end time
    """
    count = 0
    for instance in active_instances:
        instance.status = 'resolved'
        instance.ended_at = end_time
        instance.resolution_type = 'normal'
        instance.save()
        count += 1
    logger.info(f"Closed {count} active firing instances with normal resolution")

def create_new_resolved_instance(alert_group, starts_at, ends_at, annotations, generator_url):
    """
    Create a new resolved instance.
    
    Args:
        alert_group (AlertGroup): The alert group
        starts_at (datetime): Alert start time
        ends_at (datetime): Alert end time
        annotations (dict): Alert annotations
        generator_url (str): Alert generator URL
        
    Returns:
        AlertInstance: The created instance
    """
    new_instance = AlertInstance.objects.create(
        alert_group=alert_group,
        status='resolved',
        started_at=starts_at,
        ended_at=ends_at or starts_at,
        annotations=annotations,
        generator_url=generator_url,
        resolution_type='normal'
    )
    logger.info(f"Created new resolved instance (ID: {new_instance.id})")
    return new_instance

def try_match_documentation(alert_group):
    """
    Try to match documentation to this alert.
    
    Args:
        alert_group (AlertGroup): The alert group
    """
    matched_doc = match_documentation_to_alert(alert_group)
    if matched_doc:
        logger.info(f"Documentation '{matched_doc.title}' automatically linked to alert '{alert_group.name}'")
    else:
        logger.info(f"No matching documentation found for alert '{alert_group.name}'")

def acknowledge_alert(alert_group, user, comment=None):
    """
    Acknowledge an alert.
    
    Args:
        alert_group (AlertGroup): The alert group to acknowledge
        user (User): The user who acknowledged the alert
        comment (str, optional): Comment for acknowledgement
        
    Returns:
        AlertGroup: The updated alert group
    """
    # Update alert group acknowledgement status
    alert_group.acknowledged = True
    alert_group.acknowledged_by = user
    alert_group.acknowledgement_time = timezone.now()
    alert_group.save()
    
    # Get the current active firing instance if any
    active_instance = AlertInstance.objects.filter(
        alert_group=alert_group,
        status='firing',
        ended_at__isnull=True
    ).first()
    
    # Create acknowledgement history entry
    AlertAcknowledgementHistory.objects.create(
        alert_group=alert_group,
        alert_instance=active_instance,
        acknowledged_by=user,
        comment=comment
    )
    
    logger.info(f"Alert acknowledged: {alert_group.name} (ID: {alert_group.id}) by {user.username}")
    if active_instance:
        logger.info(f"Acknowledgement associated with instance ID: {active_instance.id}")
    
    return alert_group
