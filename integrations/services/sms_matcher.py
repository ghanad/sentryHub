import logging
from typing import Optional, List, Tuple

from integrations.models import SmsIntegrationRule, PhoneBook
from alerts.models import AlertGroup
from django.utils.text import slugify

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

    def resolve_recipients(self, alert_group: AlertGroup, rule: SmsIntegrationRule) -> Tuple[List[str], bool]:
        names: List[str] = []
        should_send_resolve = False
        if rule.use_sms_annotation:
            latest = alert_group.instances.order_by('-started_at').first()
            annotations = getattr(latest, 'annotations', {}) or {}
            raw = annotations.get('sms', '')
            if isinstance(raw, str):
                parts = raw.split(';')
                recipients_part = parts[0]
                names = [n.strip() for n in recipients_part.split(',') if n.strip()]
                params_part = ';'.join(parts[1:]) if len(parts) > 1 else ''
                if params_part:
                    for token in params_part.split(';'):
                        if '=' in token:
                            key, value = token.split('=', 1)
                            key_normalized = key.strip().lower()
                            value_normalized = value.strip().lower()
                            if key_normalized in {'resolve', 'resolved'} and value_normalized == 'true':
                                should_send_resolve = True
        else:
            raw = rule.recipients or ''
            names = [n.strip() for n in raw.split(',') if n.strip()]

        numbers: List[str] = []
        for name in names:
            entry = self._resolve_phonebook_entry(name)
            if entry:
                numbers.append(entry.phone_number)
        return numbers, should_send_resolve

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

    def _resolve_phonebook_entry(self, token: str) -> Optional[PhoneBook]:
        """Resolve a phonebook entry by name or reasonable aliases."""

        if not token:
            return None

        match_qs = PhoneBook.objects.filter(name__iexact=token)
        entry = match_qs.filter(is_active=True).first()
        if entry:
            return entry

        if match_qs.exists():
            logger.info("PhoneBook entry for '%s' is inactive; skipping", token)
            return None

        normalized = slugify(token)
        if not normalized:
            logger.warning("PhoneBook entry for '%s' not found", token)
            return None

        # Attempt to match OMS contacts by alias (e.g., 'Karamad OMS' -> 'karamad').
        for candidate in PhoneBook.objects.filter(is_active=True, contact_type=PhoneBook.TYPE_OMS):
            candidate_slug = slugify(candidate.name)
            trimmed_candidate_slug = candidate_slug[:-4] if candidate_slug.endswith('-oms') else candidate_slug
            if candidate_slug == normalized or trimmed_candidate_slug == normalized:
                logger.info(
                    "PhoneBook alias match for '%s' resolved to '%s'", token, candidate.name
                )
                return candidate

        logger.warning("PhoneBook entry for '%s' not found", token)
        return None
