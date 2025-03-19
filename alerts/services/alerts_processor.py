from django.utils import timezone
from dateutil.parser import parse as parse_datetime
import re

from ..models import AlertGroup, AlertInstance


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
        if status == 'firing':
            alert_group.total_firing_count += 1
        alert_group.save()
    
    # Find the latest AlertInstance
    last_instance = AlertInstance.objects.filter(
        alert_group=alert_group
    ).order_by('-started_at').first()
    
    # Create new AlertInstance or update existing
    if status == 'firing':
        # If it's a firing alert and there's no active firing instance, create one
        if not last_instance or last_instance.status != 'firing' or last_instance.ended_at:
            # Close the last instance if it exists (this shouldn't normally happen)
            if last_instance and last_instance.status == 'firing' and not last_instance.ended_at:
                last_instance.ended_at = starts_at
                last_instance.save()
                
            # Create new firing instance
            AlertInstance.objects.create(
                alert_group=alert_group,
                status=status,
                started_at=starts_at,
                ended_at=None,  # Explicitly set to None since it's firing
                annotations=annotations,
                generator_url=generator_url
            )
    else:  # status is 'resolved'
        # Find the most recent firing instance with no end time
        active_firing_instance = AlertInstance.objects.filter(
            alert_group=alert_group,
            status='firing',
            ended_at__isnull=True
        ).order_by('-started_at').first()
        
        # If we found an active firing instance, close it
        if active_firing_instance:
            active_firing_instance.ended_at = starts_at
            active_firing_instance.save()
        
        # Create a resolved instance
        AlertInstance.objects.create(
            alert_group=alert_group,
            status=status,
            started_at=starts_at,
            ended_at=starts_at,  # For 'resolved' instances, end time is same as start time
            annotations=annotations,
            generator_url=generator_url
        )
    
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