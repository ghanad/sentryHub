# integrations/services/jira_matcher.py

import logging
from typing import Dict, Optional, List # Added List import

from integrations.models import JiraIntegrationRule

logger = logging.getLogger(__name__)

class JiraRuleMatcherService:
    """
    Finds the most specific matching JiraIntegrationRule for a given set of alert labels.
    Specificity is determined by the number of matching criteria keys.
    Priority and name are used as tie-breakers.
    """

    def find_matching_rule(self, alert_labels: Dict[str, str]) -> Optional[JiraIntegrationRule]:
        """
        Finds the most specific, active JiraIntegrationRule where the match_criteria
        matches the given alert labels.

        Specificity is defined as the rule with the most keys in its match_criteria.
        Ties are broken by highest priority, then alphabetically by name.

        Args:
            alert_labels: A dictionary representing the labels of an alert.

        Returns:
            The most specific matching JiraIntegrationRule instance, or None if no rule matches.
        """
        # Get all active rules (no initial ordering needed here)
        active_rules = JiraIntegrationRule.objects.filter(is_active=True)

        matching_rules: List[JiraIntegrationRule] = []
        for rule in active_rules:
            if self._does_rule_match(rule, alert_labels):
                # Collect all rules that match
                matching_rules.append(rule)

        if not matching_rules:
            logger.debug("No active Jira integration rule matched the alert labels.")
            return None

        # Sort the matching rules to find the best one
        # 1. Most specific first (more criteria keys)
        # 2. Highest priority first (tie-breaker 1)
        # 3. Alphabetical name first (tie-breaker 2)
        matching_rules.sort(key=lambda r: (
            -len(r.match_criteria or {}), # Descending order of criteria count
            -r.priority,                 # Descending order of priority
            r.name                       # Ascending order of name
        ))

        # The best match is the first rule after sorting
        best_match = matching_rules[0]
        logger.debug(
            f"Alert labels matched {len(matching_rules)} Jira rule(s). "
            f"Selected best match by specificity/priority/name: {best_match.name} (ID: {best_match.id})"
        )
        return best_match

    def _does_rule_match(self, rule: JiraIntegrationRule, alert_labels: Dict[str, str]) -> bool:
        """ Checks if the rule's match_criteria matches the alert labels. """
        # A rule with no criteria defined cannot match any specific labels.
        # If the intent was for a rule with no criteria to be a "catch-all",
        # this logic would need adjustment, but current behavior requires criteria.
        if not rule.match_criteria:
            logger.debug(f"Jira rule '{rule.name}' (ID: {rule.id}) has no match criteria defined, skipping.")
            return False

        return self._does_criteria_match(rule.match_criteria, alert_labels)

    def _does_criteria_match(self, criteria: dict, alert_labels: Dict[str, str]) -> bool:
        """ Checks if criteria dictionary matches the alert labels. """
        # This part remains the same as before: exact matching for all defined criteria.
        if not criteria:
             # This case is handled by _does_rule_match ensuring criteria exists,
             # but kept for robustness. An empty criteria dict technically matches anything.
            return True

        for label_key, match_value in criteria.items():
            if label_key not in alert_labels:
                # Required label is missing in the alert
                # logger.debug(f"Required label '{label_key}' not found in alert labels for rule criteria.")
                return False

            alert_value = alert_labels[label_key]
            expected_value = str(match_value) # Ensure comparison is string-based
            actual_value = str(alert_value)

            # Exact matching
            if actual_value != expected_value:
                # logger.debug(f"Value '{actual_value}' did not match expected value '{expected_value}' for label '{label_key}'.")
                return False

        # If we reached here, all criteria keys present in the rule were satisfied by the alert labels
        # logger.debug("All rule criteria keys matched by alert labels.")
        return True

# Optional: Singleton instance if preferred
# jira_matcher_service_instance = JiraRuleMatcherService()