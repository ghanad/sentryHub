"""Service for matching Slack integration rules."""
import logging
from typing import Dict, Optional, List

from integrations.models import SlackIntegrationRule
from alerts.models import AlertGroup

logger = logging.getLogger(__name__)


class SlackRuleMatcherService:
    def find_matching_rule(self, alert_group: AlertGroup) -> Optional[SlackIntegrationRule]:
        """
        Return the best matching SlackIntegrationRule for a given alert group.
        Specificity is determined by the number of criteria keys.
        """
        active_rules = SlackIntegrationRule.objects.filter(is_active=True)
        matching_rules: List[SlackIntegrationRule] = []
        fp_for_log = alert_group.fingerprint  # Fingerprint for logging

        logger.debug(f"(FP: {fp_for_log}) Starting Slack rule matching for alert group.")

        for rule in active_rules:
            if self._does_rule_match(rule, alert_group):
                matching_rules.append(rule)
                logger.info(f"(FP: {fp_for_log}) Rule '{rule.name}' (ID: {rule.id}) is a potential match.")

        if not matching_rules:
            logger.info(f"(FP: {fp_for_log}) No active Slack integration rules matched the alert group.")
            return None

        # Sort by specificity (more criteria is better), then priority, then name
        matching_rules.sort(key=lambda r: (
            -(len(r.match_criteria.get("labels", {})) + len(r.match_criteria.get("fields", {}))),
            -r.priority,
            r.name
        ))

        best_match = matching_rules[0]
        logger.info(f"(FP: {fp_for_log}) Selected best match: Rule '{best_match.name}' (ID: {best_match.id}).")
        return best_match

    def _does_rule_match(self, rule: SlackIntegrationRule, alert_group: AlertGroup) -> bool:
        """
        Checks if a rule's criteria match the given alert group.
        Supports both legacy (flat dict) and new (nested "labels"/"fields") formats.
        """
        criteria = rule.match_criteria or {}
        fp_for_log = alert_group.fingerprint

        if not isinstance(criteria, dict) or not criteria:
            return False

        # --- Backward Compatibility Logic ---
        # Check if the structure is the new format or the old flat format
        if "labels" in criteria or "fields" in criteria:
            # New format
            label_criteria = criteria.get("labels", {})
            field_criteria = criteria.get("fields", {})
        else:
            # Old format: treat the whole dict as label criteria
            label_criteria = criteria
            field_criteria = {}
        # -----------------------------------

        if not label_criteria and not field_criteria:
            logger.debug(f"(FP: {fp_for_log}) Rule '{rule.name}': Skipping, as it has no valid criteria defined.")
            return False

        # Check label criteria
        for k, v in label_criteria.items():
            if alert_group.labels.get(k) != v:
                logger.debug(
                    f"(FP: {fp_for_log}) Rule '{rule.name}': Label mismatch for key '{k}'. "
                    f"Expected: '{v}', Actual: '{alert_group.labels.get(k)}'. No match."
                )
                return False

        # Check field criteria (e.g., source, jira_issue_key)
        for field_key, expected_value in field_criteria.items():
            field_name = field_key
            lookup = 'exact'
            if '__' in field_key:
                field_name, lookup = field_key.split('__', 1)

            if not hasattr(alert_group, field_name):
                logger.debug(f"(FP: {fp_for_log}) Rule '{rule.name}': Field '{field_name}' does not exist on AlertGroup. No match.")
                return False

            actual_value = getattr(alert_group, field_name)

            if lookup == 'isnull':
                is_null = (actual_value is None or actual_value == '')
                if is_null != expected_value:
                    logger.debug(
                        f"(FP: {fp_for_log}) Rule '{rule.name}': Field '{field_name}' isnull check failed. "
                        f"Expected isnull={expected_value}, but was not. No match."
                    )
                    return False
            elif lookup == 'exact':
                if str(actual_value) != str(expected_value):
                    logger.debug(
                        f"(FP: {fp_for_log}) Rule '{rule.name}': Field '{field_name}' mismatch. "
                        f"Expected: '{expected_value}', Actual: '{actual_value}'. No match."
                    )
                    return False
            else:
                logger.debug(f"(FP: {fp_for_log}) Rule '{rule.name}': Unsupported field lookup '{lookup}'. No match.")
                return False

        logger.debug(f"(FP: {fp_for_log}) Rule '{rule.name}': All criteria met. Match successful.")
        return True