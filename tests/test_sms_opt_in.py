from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch

from alerts.models import AlertGroup, AlertInstance
from integrations.models import SmsIntegrationRule, PhoneBook
from integrations.services.sms_matcher import SmsRuleMatcherService
from integrations.tasks import process_sms_for_alert_group


class SmsOptInTests(TestCase):
    def setUp(self):
        PhoneBook.objects.create(name='ali', phone_number='09100000000')
        PhoneBook.objects.create(name='reza', phone_number='09100000001')
        self.alert_group = AlertGroup.objects.create(
            fingerprint='fp1',
            name='test',
            labels={},
            severity='info',
        )

    def test_resolve_recipients_parsing(self):
        rule = SmsIntegrationRule.objects.create(
            name='rule1',
            firing_template='firing',
            resolved_template='resolved',
            use_sms_annotation=True,
        )
        AlertInstance.objects.create(
            alert_group=self.alert_group,
            status='firing',
            started_at=timezone.now(),
            annotations={'sms': 'ali,reza ; resolve = TRUE'},
        )
        matcher = SmsRuleMatcherService()
        numbers, should_send_resolve = matcher.resolve_recipients(self.alert_group, rule)
        self.assertEqual(numbers, ['09100000000', '09100000001'])
        self.assertTrue(should_send_resolve)

    def test_resolve_recipients_without_annotation_flag(self):
        rule = SmsIntegrationRule.objects.create(
            name='rule3',
            firing_template='firing',
            resolved_template='resolved',
            recipients='ali,reza',
            use_sms_annotation=False,
        )
        matcher = SmsRuleMatcherService()
        numbers, should_send_resolve = matcher.resolve_recipients(self.alert_group, rule)
        self.assertEqual(numbers, ['09100000000', '09100000001'])
        self.assertFalse(should_send_resolve)

    def test_resolved_sms_sent_only_with_opt_in(self):
        rule = SmsIntegrationRule.objects.create(
            name='rule2',
            firing_template='firing',
            resolved_template='resolved',
            use_sms_annotation=True,
        )
        # First instance without resolve=true -> no SMS
        self.alert_group.current_status = 'resolved'
        self.alert_group.save()
        AlertInstance.objects.create(
            alert_group=self.alert_group,
            status='resolved',
            started_at=timezone.now(),
            annotations={'sms': 'ali'},
        )
        with patch('integrations.tasks.SmsService.send_bulk') as mock_send:
            process_sms_for_alert_group.apply((self.alert_group.id, rule.id))
            mock_send.assert_not_called()

        # Update annotation with resolve=true -> SMS sent
        AlertInstance.objects.create(
            alert_group=self.alert_group,
            status='resolved',
            started_at=timezone.now(),
            annotations={'sms': 'ali;resolve=true'},
        )
        with patch('integrations.tasks.SmsService.send_bulk') as mock_send:
            process_sms_for_alert_group.apply((self.alert_group.id, rule.id))
            mock_send.assert_called_once()
            args, _ = mock_send.call_args
            self.assertIn('resolved', args[1])
