from django.utils import timezone
from dateutil.parser import parse as parse_datetime
import re
import logging
import json

from ..models import AlertGroup, AlertInstance, AlertAcknowledgementHistory, SilenceRule
from docs.services.documentation_matcher import match_documentation_to_alert
from .silence_matcher import check_alert_silence
from .jira_matcher import JiraRuleMatcherService
from ..tasks import process_jira_for_alert_group

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
    elif not is_silenced and alert_group.is_silenced:
        logger.info(f"Alert {alert_group.name} (Group ID: {alert_group.id}) was silenced but is no longer.")

    # --- Jira Integration Check (Only if NOT silenced) ---
    if not is_silenced:
        logger.debug(f"Checking Jira rules for non-silenced alert group {fingerprint} with status {status}")
        jira_matcher_service = JiraRuleMatcherService()
        matching_rule = jira_matcher_service.find_matching_rule(labels)

        if matching_rule:
            logger.info(f"Alert group {fingerprint} matched Jira rule '{matching_rule.name}'. Triggering Jira processing task.")
            try:
                process_jira_for_alert_group.delay(
                    alert_group_id=alert_group.id,
                    rule_id=matching_rule.id,
                    alert_status=status
                )
            except Exception as e:
                logger.error(f"Failed to queue Jira processing task for alert group {alert_group.id}: {e}", exc_info=True)

    # Process the alert
    if status == 'firing':
        process_firing_alert(alert_group, labels, fingerprint, starts_at, annotations, generator_url)
    else:  # status is 'resolved'
        process_resolved_alert(alert_group, labels, fingerprint, starts_at, ends_at, annotations, generator_url)
    
    # Try to find related documentation for this alert
    try_match_documentation(alert_group)
    
    return alert_group

def extract_alert_data(alert_data):
    """Extract relevant data from the alert."""
    fingerprint = alert_data.get('fingerprint')
    status = alert_data.get('status')
    labels = alert_data.get('labels', {})
    annotations = alert_data.get('annotations', {})
    starts_at = parse_datetime(alert_data.get('startsAt'))
    ends_at = parse_datetime(alert_data.get('endsAt')) if alert_data.get('endsAt') != '0001-01-01T00:00:00Z' else None
    generator_url = alert_data.get('generatorURL')
    return fingerprint, status, labels, annotations, starts_at, ends_at, generator_url

def get_or_create_alert_group(fingerprint, status, labels):
    """Get or create an AlertGroup."""
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
    
    return alert_group

def process_firing_alert(alert_group, labels, fingerprint, starts_at, annotations, generator_url):
    """Process a firing alert."""
    if not is_duplicate_firing(alert_group, starts_at):
        create_new_firing_instance(alert_group, starts_at, annotations, generator_url)

def process_resolved_alert(alert_group, labels, fingerprint, starts_at, ends_at, annotations, generator_url):
    """Process a resolved alert."""
    if not is_duplicate_resolved(alert_group, starts_at, ends_at):
        matching_firing = get_matching_firing_instance(alert_group, starts_at)
        if matching_firing:
            update_to_resolved(matching_firing, ends_at or starts_at)
        else:
            create_new_resolved_instance(alert_group, starts_at, ends_at, annotations, generator_url)

def is_duplicate_firing(alert_group, starts_at):
    """Check if the firing alert is a duplicate."""
    return AlertInstance.objects.filter(
        alert_group=alert_group,
        status='firing',
        started_at=starts_at,
        ended_at__isnull=True
    ).exists()

def get_active_firing_instance(alert_group):
    """Get the active firing instance for an alert group."""
    return AlertInstance.objects.filter(
        alert_group=alert_group,
        status='firing',
        ended_at__isnull=True
    ).first()

def create_new_firing_instance(alert_group, starts_at, annotations, generator_url):
    """Create a new firing instance."""
    AlertInstance.objects.create(
        alert_group=alert_group,
        status='firing',
        started_at=starts_at,
        annotations=annotations,
        generator_url=generator_url
    )

def is_duplicate_resolved(alert_group, starts_at, ends_at):
    """Check if the resolved alert is a duplicate."""
    return AlertInstance.objects.filter(
        alert_group=alert_group,
        status='resolved',
        started_at=starts_at,
        ended_at=ends_at or starts_at
    ).exists()

def get_matching_firing_instance(alert_group, starts_at):
    """Get a firing instance that matches the start time."""
    return AlertInstance.objects.filter(
        alert_group=alert_group,
        status='firing',
        started_at=starts_at
    ).first()

def update_to_resolved(instance, end_time):
    """Update a firing instance to resolved status."""
    instance.status = 'resolved'
    instance.ended_at = end_time
    instance.save()

def create_new_resolved_instance(alert_group, starts_at, ends_at, annotations, generator_url):
    """Create a new resolved instance."""
    AlertInstance.objects.create(
        alert_group=alert_group,
        status='resolved',
        started_at=starts_at,
        ended_at=ends_at or starts_at,
        annotations=annotations,
        generator_url=generator_url
    )

def try_match_documentation(alert_group):
    """Try to match documentation to this alert."""
    matched_doc = match_documentation_to_alert(alert_group)
    if matched_doc:
        logger.info(f"Matched documentation for alert: {alert_group.name}")

def acknowledge_alert(alert_group, user, comment=None):
    """Acknowledge an alert."""
    alert_group.acknowledged = True
    alert_group.acknowledged_by = user
    alert_group.acknowledgement_time = timezone.now()
    alert_group.save()
    
    active_instance = get_active_firing_instance(alert_group)
    AlertAcknowledgementHistory.objects.create(
        alert_group=alert_group,
        alert_instance=active_instance,
        acknowledged_by=user,
        comment=comment
    )
    return alert_group
