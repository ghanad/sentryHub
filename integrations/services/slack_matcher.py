"""Service for matching Slack integration rules."""
import logging
from typing import Dict, Optional, List

from integrations.models import SlackIntegrationRule

logger = logging.getLogger(__name__)


class SlackRuleMatcherService:
    def find_matching_rule(self, alert_labels: Dict[str, str]) -> Optional[SlackIntegrationRule]:
        """Return the best matching SlackIntegrationRule for given labels."""
        active_rules = SlackIntegrationRule.objects.filter(is_active=True)
        matching: List[SlackIntegrationRule] = []
        for rule in active_rules:
            criteria = rule.match_criteria or {}
            if all(alert_labels.get(k) == v for k, v in criteria.items()):
                matching.append(rule)
        if not matching:
            return None
        matching.sort(key=lambda r: (-r.priority, r.name))
        return matching[0]
