import logging
import re
from typing import Dict, Optional, List

from integrations.models import JiraIntegrationRule, JiraRuleMatcher

logger = logging.getLogger(__name__)

class JiraRuleMatcherService:
    """
    Finds the first matching JiraIntegrationRule for a given set of alert labels.
    """

    def find_matching_rule(self, alert_labels: Dict[str, str]) -> Optional[JiraIntegrationRule]:
        """
        Finds the highest priority, active JiraIntegrationRule where ALL associated
        matchers match the given alert labels.

        Args:
            alert_labels: A dictionary representing the labels of an alert.

        Returns:
            The matching JiraIntegrationRule instance, or None if no rule matches.
        """
        # Get active rules, ordered by priority (highest first)
        # Prefetch related matchers for efficiency
        active_rules = JiraIntegrationRule.objects.filter(is_active=True).prefetch_related('matchers').order_by('-priority', 'name')

        for rule in active_rules:
            if self._does_rule_match(rule, alert_labels):
                logger.debug(f"Alert labels matched Jira rule: {rule.name} (ID: {rule.id})")
                return rule

        logger.debug("No active Jira integration rule matched the alert labels.")
        return None

    def _does_rule_match(self, rule: JiraIntegrationRule, alert_labels: Dict[str, str]) -> bool:
        """ Checks if ALL matchers associated with the rule match the alert labels. """
        # If a rule has no matchers, should it match? Assume no.
        if not rule.matchers.exists():
             logger.debug(f"Jira rule '{rule.name}' (ID: {rule.id}) has no matchers defined, skipping.")
             return False

        # Check if all associated matchers are satisfied
        all_matchers_satisfied = True
        for matcher in rule.matchers.all():
            if not self._does_matcher_match(matcher, alert_labels):
                all_matchers_satisfied = False
                # logger.debug(f"Matcher '{matcher.name}' (ID: {matcher.id}) did not match for rule '{rule.name}'.")
                break # No need to check other matchers for this rule

        return all_matchers_satisfied


    def _does_matcher_match(self, matcher: JiraRuleMatcher, alert_labels: Dict[str, str]) -> bool:
        """ Checks if a single matcher's criteria are met by the alert labels. """
        # If a matcher has no criteria, should it match? Assume yes (vacuously true).
        if not matcher.match_criteria:
            return True

        for label_key, match_value in matcher.match_criteria.items():
            if label_key not in alert_labels:
                # Required label is missing in the alert
                # logger.debug(f"Matcher '{matcher.name}': Required label '{label_key}' not found in alert labels.")
                return False

            alert_value = alert_labels[label_key]
            expected_value = str(match_value) # Ensure comparison is string-based
            actual_value = str(alert_value)

            if matcher.is_regex:
                try:
                    if not re.fullmatch(expected_value, actual_value):
                        # Regex does not match
                        # logger.debug(f"Matcher '{matcher.name}': Regex '{expected_value}' did not match value '{actual_value}' for label '{label_key}'.")
                        return False
                except re.error:
                    logger.error(f"Invalid regex pattern '{expected_value}' in JiraRuleMatcher ID {matcher.id}", exc_info=True)
                    # Treat invalid regex as non-matching
                    return False
            else:
                if actual_value != expected_value:
                    # Exact string does not match
                    # logger.debug(f"Matcher '{matcher.name}': Value '{actual_value}' did not match expected value '{expected_value}' for label '{label_key}'.")
                    return False

        # If we reached here, all criteria in this specific matcher were satisfied
        logger.debug(f"Matcher '{matcher.name}' (ID: {matcher.id}) criteria met by alert labels.")
        return True

# Optional: Singleton instance if preferred
# jira_matcher_service_instance = JiraRuleMatcherService()