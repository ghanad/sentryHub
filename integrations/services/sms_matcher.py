import logging
from typing import Optional, List

from integrations.models import SmsIntegrationRule, PhoneBook
from alerts.models import AlertGroup

logger = logging.getLogger(__name__)


class SmsRuleMatcherService:
    """Service to match SmsIntegrationRule and resolve recipients."""

    def find_matching_rule(self, alert_group: AlertGroup) -> Optional[SmsIntegrationRule]:
        active_rules = SmsIntegrationRule.objects.filter(is_active=True)
        matching: List[SmsIntegrationRule] = []
        for rule in active_rules:
            if self._does_rule_match(rule, alert_group):
                matching.append(rule)
                logger.info("Rule '%s' is a potential match.", rule.name)
        if not matching:
            return None
        matching.sort(key=lambda r: (-len(r.match_criteria or {}), -r.priority, r.name))
        return matching[0]

    def resolve_recipients(self, alert_group: AlertGroup, rule: SmsIntegrationRule) -> List[str]:
        names: List[str] = []
        if rule.use_sms_annotation:
            latest = alert_group.instances.order_by('-started_at').first()
            annotations = getattr(latest, 'annotations', {}) or {}
            raw = annotations.get('sms', '')
            if isinstance(raw, str):
                names = [n.strip() for n in raw.split(',') if n.strip()]
        else:
            raw = rule.recipients or ''
            names = [n.strip() for n in raw.split(',') if n.strip()]

        numbers: List[str] = []
        for name in names:
            try:
                entry = PhoneBook.objects.get(name__iexact=name)
                numbers.append(entry.phone_number)
            except PhoneBook.DoesNotExist:
                logger.warning("PhoneBook entry for '%s' not found", name)
        return numbers

    def _does_rule_match(self, rule: SmsIntegrationRule, alert_group: AlertGroup) -> bool:
        criteria = rule.match_criteria or {}
        if not isinstance(criteria, dict):
            return False
        if not criteria:
            return True
        for key, expected in criteria.items():
            if key.startswith('labels__'):
                label_key = key.split('__', 1)[1]
                if str(alert_group.labels.get(label_key)) != str(expected):
                    return False
            else:
                field_name, lookup = key, 'exact'
                if '__' in key:
                    field_name, lookup = key.split('__', 1)
                if not hasattr(alert_group, field_name):
                    return False
                actual = getattr(alert_group, field_name)
                if lookup == 'isnull':
                    is_null = actual is None or actual == ''
                    if is_null != expected:
                        return False
                elif str(actual) != str(expected):
                    return False
        return True
