import logging
import re
from typing import Dict, Optional

from integrations.models import JiraIntegrationRule

logger = logging.getLogger(__name__)

class JiraRuleMatcherService:
    """
    Finds the first matching JiraIntegrationRule for a given set of alert labels.
    """

    def find_matching_rule(self, alert_labels: Dict[str, str]) -> Optional[JiraIntegrationRule]:
        """
        Finds the highest priority, active JiraIntegrationRule where the match_criteria
        matches the given alert labels.

        Args:
            alert_labels: A dictionary representing the labels of an alert.

        Returns:
            The matching JiraIntegrationRule instance, or None if no rule matches.
        """
        # Get active rules, ordered by priority (highest first)
        active_rules = JiraIntegrationRule.objects.filter(
            is_active=True
        ).order_by('-priority', 'name')

        for rule in active_rules:
            if self._does_rule_match(rule, alert_labels):
                logger.debug(f"Alert labels matched Jira rule: {rule.name} (ID: {rule.id})")
                return rule

        logger.debug("No active Jira integration rule matched the alert labels.")
        return None

    def _does_rule_match(self, rule: JiraIntegrationRule, alert_labels: Dict[str, str]) -> bool:
        """ Checks if the rule's match_criteria matches the alert labels. """
        if not rule.match_criteria:
            logger.debug(f"Jira rule '{rule.name}' (ID: {rule.id}) has no match criteria defined, skipping.")
            return False

        return self._does_criteria_match(rule.match_criteria, alert_labels)

    def _does_criteria_match(self, criteria: dict, alert_labels: Dict[str, str]) -> bool:
        """ Checks if criteria dictionary matches the alert labels. """
        if not criteria:
            return True

        for label_key, match_value in criteria.items():
            if label_key not in alert_labels:
                # Required label is missing in the alert
                logger.debug(f"Required label '{label_key}' not found in alert labels.")
                return False

            alert_value = alert_labels[label_key]
            expected_value = str(match_value) # Ensure comparison is string-based
            actual_value = str(alert_value)

            # For now, we'll do exact matching only (as per task requirements)
            # Can be extended later to support regex if needed
            if actual_value != expected_value:
                # Exact string does not match
                logger.debug(f"Value '{actual_value}' did not match expected value '{expected_value}' for label '{label_key}'.")
                return False

        # If we reached here, all criteria were satisfied
        logger.debug("All criteria matched by alert labels.")
        return True

# Optional: Singleton instance if preferred
# jira_matcher_service_instance = JiraRuleMatcherService()