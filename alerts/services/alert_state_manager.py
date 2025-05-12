# alerts/services/alert_state_manager.py
from django.utils import timezone
from django.db import transaction
from typing import Tuple, Optional
import logging
from django.db.models import F
import json # Keep import if used elsewhere, e.g. logging
import pytz # Keep import if used elsewhere

from ..models import AlertGroup, AlertInstance

logger = logging.getLogger(__name__)

def update_alert_state(parsed_alert_data: dict) -> Tuple[Optional[AlertGroup], Optional[AlertInstance]]:
    """
    Update alert state in database based on parsed alert data.
    Ensures only one 'firing' instance exists per group at any time by marking
    previous firing instances as 'resolved' (inferred) without setting an end time.

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
            ends_at = parsed_alert_data['ends_at'] # This might be None for firing alerts
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
                    'instance': labels.get('instance'),
                    'first_occurrence': timezone.now(), # Set on creation
                    'last_occurrence': timezone.now()  # Initial value
                }
            )

            if not created:
                original_status = alert_group.current_status # Store original status
                # Update fields that might change
                alert_group.current_status = status
                alert_group.last_occurrence = timezone.now()
                # Optionally update these based on new data, if desired
                # alert_group.name = labels.get('alertname', 'Unknown Alert')
                # alert_group.labels = labels # Be careful updating labels on existing groups
                # alert_group.severity = labels.get('severity', 'warning')
                # alert_group.instance = labels.get('instance')

                # Increment firing count ONLY if transitioning TO firing
                if status == 'firing' and original_status != 'firing': # Use original_status in condition
                     alert_group.total_firing_count = F('total_firing_count') + 1 # Use F() for atomic update
                     alert_group.save(update_fields=['current_status', 'last_occurrence', 'total_firing_count'])
                else:
                     alert_group.save(update_fields=['current_status', 'last_occurrence'])
            else:
                # total_firing_count defaults to 1, which is correct.
                pass


            # Handle alert instance based on status
            alert_instance = None
            if status == 'firing':
                # --- START: Modified Logic to mark previous firing instances ---
                previous_firing_instances = AlertInstance.objects.filter(
                    alert_group=alert_group,
                    status='firing',
                    ended_at__isnull=True
                ).exclude(started_at=starts_at) # Exclude the one we might create

                if previous_firing_instances.exists():
                    resolved_count = previous_firing_instances.update(
                        status='resolved',
                        # ended_at=starts_at, # REMOVED: Keep ended_at as NULL
                        resolution_type='inferred' # Keep marking as inferred
                    )
                    # Adjust log message
                    logger.info(f"Marked {resolved_count} previous firing instance(s) as 'resolved' (inferred, ended_at=NULL) for AlertGroup {alert_group.id} (FP: {alert_group.fingerprint}) due to new firing event starting at {starts_at}.")
                 # --- END: Modified Logic ---

                if not _is_duplicate_firing(alert_group, starts_at):
                    alert_instance = _create_firing_instance(
                        alert_group, starts_at, annotations, generator_url
                    )
                else:
                     logger.warning(f"Duplicate firing event detected for AlertGroup {alert_group.id} (FP: {alert_group.fingerprint}) starting at {starts_at}. Skipping instance creation.")

            else:  # resolved
                if not _is_duplicate_resolved(alert_group, starts_at, ends_at):
                    matching_firing = _get_matching_firing_instance(alert_group, starts_at)
                    if matching_firing:
                        # Resolve the specific firing instance that matches the start time
                        # Use the provided ends_at. The helper function _update_to_resolved handles None.
                        alert_instance = _update_to_resolved(matching_firing, ends_at, 'normal') # Mark as normal resolution
                    else:
                         # If no matching firing instance, check for ANY other open firing instances
                         other_open_firing = AlertInstance.objects.filter(
                             alert_group=alert_group,
                             status='firing',
                             ended_at__isnull=True
                         ).order_by('-started_at').first()

                         if other_open_firing:
                              # Resolve the LATEST open one as inferred, keeping ended_at NULL as per the primary request
                              logger.warning(f"Received resolved event for AlertGroup {alert_group.id} (FP: {alert_group.fingerprint}) starting at {starts_at}, but no exact firing match found. Marking latest open instance ({other_open_firing.id}) as 'resolved' (inferred, ended_at=NULL).")
                              alert_instance = _update_to_resolved(other_open_firing, None, 'inferred') # Pass None for end_time
                         else:
                              # No matching firing AND no other open firing instances. Create resolved directly.
                              logger.warning(f"Received resolved event for AlertGroup {alert_group.id} (FP: {alert_group.fingerprint}) starting at {starts_at}, but no matching or open firing instance found. Creating resolved instance directly.")
                              effective_end_time = ends_at or starts_at
                              alert_instance = _create_resolved_instance(
                                  alert_group, starts_at, effective_end_time, annotations, generator_url, 'normal'
                              )
                else:
                     logger.warning(f"Duplicate resolved event detected for AlertGroup {alert_group.id} starting at {starts_at}. Skipping.")


            return alert_group, alert_instance

    except Exception as e:
        fingerprint = locals().get('fingerprint', 'UNKNOWN')
        group_id = getattr(locals().get('alert_group'), 'id', 'N/A')
        logger.error(f"Error processing alert update for fingerprint {fingerprint} (Group ID: {group_id}): {e}", exc_info=True)
        raise e


# --- Helper Functions (Need slight adjustment) ---

def _is_duplicate_firing(alert_group, starts_at):
    """Check if the firing alert is a duplicate based on start time."""
    # We only care if an identical firing event (same start time) exists.
    # Whether a previous *different* firing event is open is handled above.
    return AlertInstance.objects.filter(
        alert_group=alert_group,
        status='firing',
        started_at=starts_at,
    ).exists()

def _get_matching_firing_instance(alert_group, starts_at):
    """Get an open firing instance that matches the start time."""
    return AlertInstance.objects.filter(
        alert_group=alert_group,
        status='firing',
        started_at=starts_at,
        ended_at__isnull=True # Only match currently open firing instances
    ).first()

def _create_firing_instance(alert_group, starts_at, annotations, generator_url):
    """Create a new firing instance."""
    logger.info(f"Creating new 'firing' instance for AlertGroup {alert_group.id} (FP: {alert_group.fingerprint}) starting at {starts_at}")
    return AlertInstance.objects.create(
        alert_group=alert_group,
        status='firing',
        started_at=starts_at,
        annotations=annotations,
        generator_url=generator_url,
        ended_at=None, # Explicitly null
        resolution_type=None # Explicitly null
    )

def _is_duplicate_resolved(alert_group, starts_at, ends_at):
    """Check if an identical resolved instance already exists."""
    logger.debug(f"Checking for duplicate resolved alert - group: {alert_group.fingerprint}, starts_at: {starts_at}, ends_at: {ends_at}")

    query = AlertInstance.objects.filter(
        alert_group=alert_group,
        status='resolved',
        started_at=starts_at
    )
    # If ends_at was provided, require it to match as well
    if ends_at:
        query = query.filter(ended_at=ends_at)
    else:
         # If Alertmanager didn't provide ends_at for resolved,
         # maybe we check for inferred resolutions without an end time?
         # Or maybe we only consider it a duplicate if *both* start/end match?
         # Let's stick to requiring matching ends_at if provided.
         # If ends_at is None, we only check for resolved with same start_at AND ended_at is NULL
         query = query.filter(ended_at__isnull=True)

    exists = query.exists()
    logger.debug(f"Duplicate resolved check result: {exists}")
    return exists

def _update_to_resolved(instance, end_time, resolution_type):
    """Update a firing instance to resolved status."""
    instance.status = 'resolved'
    # Only set ended_at if it's provided (i.e., not None)
    instance.ended_at = end_time # Allows end_time to be None
    instance.resolution_type = resolution_type
    update_fields = ['status', 'resolution_type']
    if end_time is not None:
        update_fields.append('ended_at') # Only update ended_at if it's not None

    instance.save(update_fields=update_fields)
    end_time_str = f"at {end_time}" if end_time else "(ended_at=NULL)"
    logger.info(f"Updated instance {instance.id} to 'resolved' (Type: {resolution_type}) {end_time_str} for AlertGroup {instance.alert_group.id} (FP: {instance.alert_group.fingerprint})")
    return instance

def _create_resolved_instance(alert_group, starts_at, ends_at, annotations, generator_url, resolution_type):
    """Create a new resolved instance."""
    end_time_str = f"ended at {ends_at}" if ends_at else "ended_at=NULL"
    logger.info(f"Creating new 'resolved' instance (Type: {resolution_type}) for AlertGroup {alert_group.id} (FP: {alert_group.fingerprint}) starting at {starts_at}, {end_time_str}")
    return AlertInstance.objects.create(
        alert_group=alert_group,
        status='resolved',
        started_at=starts_at,
        ended_at=ends_at, # Can be None if ends_at from payload was None
        annotations=annotations,
        generator_url=generator_url,
        resolution_type=resolution_type
    )