from django.utils import timezone
from ..models import SilenceRule, AlertGroup
import logging

logger = logging.getLogger(__name__)

def check_alert_silence(alert_group: AlertGroup):
    """
    Checks if an AlertGroup matches any active SilenceRule based on exact label matching.
    Updates the alert_group's is_silenced status and silenced_until.

    Args:
        alert_group: The AlertGroup instance to check.

    Returns:
        bool: True if the alert is currently silenced, False otherwise.
    """
    now = timezone.now()
    alert_labels = alert_group.labels

    # Find potentially matching active rules
    # Optimization: Filter rules that could possibly match based on keys present in alert_labels
    # This might be complex to implement efficiently with JSONField lookups across different DBs.
    # For now, fetch all active rules and filter in Python.
    active_rules = SilenceRule.objects.filter(starts_at__lte=now, ends_at__gt=now)

    matching_rule = None
    latest_end_time = None

    for rule in active_rules:
        rule_matchers = rule.matchers
        is_match = True

        # Ensure rule_matchers is a dictionary before proceeding
        if not isinstance(rule_matchers, dict) or not rule_matchers:
            logger.debug(f"Skipping rule {rule.id}: Invalid or empty matchers ({rule_matchers})")
            continue

        # Exact match logic: all rule matchers must exist and match in alert labels
        for key, value in rule_matchers.items():
            if alert_labels.get(key) != value:
                is_match = False
                break  # This rule doesn't match

        if is_match:
            # Found a matching active rule
            logger.debug(f"AlertGroup {alert_group.id} matched rule {rule.id}")
            matching_rule = rule # Keep track of the last matching rule (or first, depending on desired logic)
            if latest_end_time is None or rule.ends_at > latest_end_time:
                latest_end_time = rule.ends_at
            # Continue checking other rules to find the one with the latest end time

    # Update AlertGroup based on match results
    was_silenced = alert_group.is_silenced
    is_now_silenced = matching_rule is not None

    updated_fields = []
    needs_save = False

    if is_now_silenced:
        if not was_silenced or alert_group.silenced_until != latest_end_time:
            alert_group.is_silenced = True
            alert_group.silenced_until = latest_end_time
            updated_fields.extend(['is_silenced', 'silenced_until'])
            needs_save = True
            logger.info(f"AlertGroup {alert_group.id} ({alert_group.name}) is now SILENCED until {latest_end_time} by rule {matching_rule.id}")
        # else: Alert was already silenced, and the end time hasn't changed, no update needed.
        
        # Return True as it is currently silenced
        if needs_save:
            alert_group.save(update_fields=updated_fields)
        return True

    else:
        # No active rule matched
        if was_silenced:
            alert_group.is_silenced = False
            alert_group.silenced_until = None
            updated_fields.extend(['is_silenced', 'silenced_until'])
            needs_save = True
            logger.info(f"AlertGroup {alert_group.id} ({alert_group.name}) is no longer silenced (no matching active rules).")
        # else: Alert was not silenced, and still isn't, no update needed.

        # Return False as it is not currently silenced
        if needs_save:
            alert_group.save(update_fields=updated_fields)
        return False
