from django.utils import timezone
from django.db import transaction
from typing import Tuple, Optional
import logging

from ..models import AlertGroup, AlertInstance

logger = logging.getLogger(__name__)

def update_alert_state(parsed_alert_data: dict) -> Tuple[Optional[AlertGroup], Optional[AlertInstance]]:
    """
    Update alert state in database based on parsed alert data.
    
    Args:
        parsed_alert_data: Standardized alert data from payload_parser
        
    Returns:
        Tuple of (AlertGroup, AlertInstance) that were created/updated
        Returns (None, None) if no changes were made or error occurred
    """
    try:
        with transaction.atomic():
            fingerprint = parsed_alert_data['fingerprint']
            status = parsed_alert_data['status']
            labels = parsed_alert_data['labels']
            starts_at = parsed_alert_data['starts_at']
            ends_at = parsed_alert_data['ends_at']
            annotations = parsed_alert_data['annotations']
            generator_url = parsed_alert_data['generator_url']
            
            # Get or create AlertGroup
            alert_group, created = AlertGroup.objects.get_or_create(
                fingerprint=fingerprint,
                defaults={
                    'name': labels.get('alertname', 'Unknown Alert'),
                    'labels': labels,
                    'severity': labels.get('severity', 'warning'),
                    'current_status': status,
                    'instance': labels.get('instance')
                }
            )
            
            if not created:
                alert_group.current_status = status
                alert_group.last_occurrence = timezone.now()
                alert_group.save(update_fields=['current_status', 'last_occurrence'])
            
            # Handle alert instance based on status
            alert_instance = None
            if status == 'firing':
                if not _is_duplicate_firing(alert_group, starts_at):
                    alert_instance = _create_firing_instance(
                        alert_group, starts_at, annotations, generator_url
                    )
            else:  # resolved
                if not _is_duplicate_resolved(alert_group, starts_at, ends_at):
                    matching_firing = _get_matching_firing_instance(alert_group, starts_at)
                    if matching_firing:
                        alert_instance = _update_to_resolved(matching_firing, ends_at or starts_at)
                    else:
                        alert_instance = _create_resolved_instance(
                            alert_group, starts_at, ends_at, annotations, generator_url
                        )
            
            return alert_group, alert_instance
    
    except Exception as e:
        # Use getattr for safer access in case alert_group is None or problematic
        group_identifier = getattr(locals().get('alert_group'), 'fingerprint', 'UNKNOWN')
        logger.error(f"Error processing alert group {group_identifier}: {e}", exc_info=True)
        raise e # Re-raise the exception to mark the Celery task as failed

def _is_duplicate_firing(alert_group, starts_at):
    """Check if the firing alert is a duplicate."""
    return AlertInstance.objects.filter(
        alert_group=alert_group,
        status='firing',
        started_at=starts_at,
        ended_at__isnull=True
    ).exists()

def _get_matching_firing_instance(alert_group, starts_at):
    """Get a firing instance that matches the start time."""
    return AlertInstance.objects.filter(
        alert_group=alert_group,
        status='firing',
        started_at=starts_at
    ).first()

def _create_firing_instance(alert_group, starts_at, annotations, generator_url):
    """Create a new firing instance."""
    return AlertInstance.objects.create(
        alert_group=alert_group,
        status='firing',
        started_at=starts_at,
        annotations=annotations,
        generator_url=generator_url
    )

def _is_duplicate_resolved(alert_group, starts_at, ends_at):
    """Check if the resolved alert is a duplicate."""
    logger.debug(f"Checking for duplicate resolved alert - group: {alert_group.fingerprint}, starts_at: {starts_at}, ends_at: {ends_at}")
    
    # Only check for exact duplicates if ends_at is provided
    if ends_at:
        exists = AlertInstance.objects.filter(
            alert_group=alert_group,
            status='resolved',
            started_at=starts_at,
            ended_at=ends_at
        ).exists()
        logger.debug(f"Exact duplicate check result: {exists}")
        return exists
    
    # For alerts without explicit end time, be more lenient
    exists = AlertInstance.objects.filter(
        alert_group=alert_group,
        status='resolved',
        started_at=starts_at
    ).exists()
    logger.debug(f"Lenient duplicate check result: {exists}")
    return exists

def _update_to_resolved(instance, end_time):
    """Update a firing instance to resolved status."""
    instance.status = 'resolved'
    instance.ended_at = end_time
    instance.save()
    return instance

def _create_resolved_instance(alert_group, starts_at, ends_at, annotations, generator_url):
    """Create a new resolved instance."""
    return AlertInstance.objects.create(
        alert_group=alert_group,
        status='resolved',
        started_at=starts_at,
        ended_at=ends_at or starts_at,
        annotations=annotations,
        generator_url=generator_url
    )