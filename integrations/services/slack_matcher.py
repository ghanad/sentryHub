"""Service for matching Slack integration rules."""
import logging
from typing import Dict, Optional, List

from integrations.models import SlackIntegrationRule
from alerts.models import AlertGroup  # Import AlertGroup

logger = logging.getLogger(__name__)


class SlackRuleMatcherService:
    def find_matching_rule(self, alert_group: AlertGroup) -> Optional[SlackIntegrationRule]:
        """
        Return the best matching SlackIntegrationRule for a given alert group.
        Specificity is determined by the number of criteria keys.
        """
        active_rules = SlackIntegrationRule.objects.filter(is_active=True)
        matching_rules: List[SlackIntegrationRule] = []

        for rule in active_rules:
            if self._does_rule_match(rule, alert_group):
                matching_rules.append(rule)

        if not matching_rules:
            return None

        # Sort by specificity (more criteria is better), then priority, then name
        matching_rules.sort(key=lambda r: (
            -(len(r.match_criteria.get("labels", {})) + len(r.match_criteria.get("fields", {}))),  # Specificity
            -r.priority,
            r.name
        ))
        return matching_rules[0]

    def _does_rule_match(self, rule: SlackIntegrationRule, alert_group: AlertGroup) -> bool:
        """Checks if a rule's criteria match the given alert group."""
        criteria = rule.match_criteria or {}
        if not isinstance(criteria, dict) or not criteria:  # An empty rule matches nothing
            return False

        label_criteria = criteria.get("labels", {})
        field_criteria = criteria.get("fields", {})

        # A rule must have at least one criterion to match
        if not label_criteria and not field_criteria:
            return False

        # Check label criteria
        if not all(alert_group.labels.get(k) == v for k, v in label_criteria.items()):
            return False

        # Check field criteria (e.g., source, jira_issue_key)
        for field_key, expected_value in field_criteria.items():
            field_name = field_key
            lookup = 'exact'
            if '__' in field_key:
                field_name, lookup = field_key.split('__', 1)

            if not hasattr(alert_group, field_name):
                return False  # Field doesn't exist on the model

            actual_value = getattr(alert_group, field_name)

            if lookup == 'isnull':
                is_null = (actual_value is None or actual_value == '')
                if is_null != expected_value:
                    return False
            elif lookup == 'exact':
                if str(actual_value) != str(expected_value):
                    return False
            else:
                # Unsupported lookup
                return False

        return True