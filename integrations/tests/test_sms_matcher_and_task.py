from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from alerts.models import AlertGroup
from integrations.models import PhoneBook, SmsIntegrationRule
from integrations.services.sms_matcher import SmsRuleMatcherService
from integrations.exceptions import SmsNotificationError
from integrations.tasks import process_sms_for_alert_group
from celery.exceptions import Retry


class SmsMatcherTests(TestCase):
    def setUp(self):
        self.alert_group = AlertGroup.objects.create(
            fingerprint='fp1',
            name='AG',
            labels={'env': 'prod'},
            source='prometheus',
        )

    def test_annotation_priority(self):
        PhoneBook.objects.create(name='alice', phone_number='1')
        PhoneBook.objects.create(name='bob', phone_number='2')
        self.alert_group.instances.create(status='firing', started_at=timezone.now(), annotations={'sms': 'alice,bob'})
        rule = SmsIntegrationRule.objects.create(name='r', match_criteria={}, use_sms_annotation=True, firing_template='hi')
        matcher = SmsRuleMatcherService()
        nums = matcher.resolve_recipients(self.alert_group, rule)
        self.assertEqual(set(nums), {'1', '2'})

    def test_rule_recipients_fallback(self):
        PhoneBook.objects.create(name='alice', phone_number='1')
        rule = SmsIntegrationRule.objects.create(name='r', match_criteria={}, recipients='alice', firing_template='hi')
        matcher = SmsRuleMatcherService()
        nums = matcher.resolve_recipients(self.alert_group, rule)
        self.assertEqual(nums, ['1'])


class SmsTaskTests(TestCase):
    @patch('integrations.tasks.SmsService')
    def test_process_sms_for_alert_group(self, service_cls):
        mock_service = service_cls.return_value
        mock_service.send_bulk.return_value = True
        PhoneBook.objects.create(name='alice', phone_number='1')
        alert_group = AlertGroup.objects.create(fingerprint='fp2', name='AG2', labels={}, source='prometheus')
        rule = SmsIntegrationRule.objects.create(name='r', match_criteria={}, recipients='alice', firing_template='msg')
        process_sms_for_alert_group(alert_group.id, rule.id)
        mock_service.send_bulk.assert_called_once_with(['1'], 'msg', fingerprint='fp2')

    @patch('integrations.tasks.SmsService')
    @patch('integrations.tasks.process_sms_for_alert_group.retry', side_effect=Retry('boom'))
    def test_task_retries_on_error(self, retry_mock, service_cls):
        service_cls.return_value.send_bulk.side_effect = SmsNotificationError('net')
        PhoneBook.objects.create(name='alice', phone_number='1')
        alert_group = AlertGroup.objects.create(fingerprint='fp3', name='AG3', labels={}, source='prometheus')
        rule = SmsIntegrationRule.objects.create(name='r', match_criteria={}, recipients='alice', firing_template='msg')
        with self.assertRaises(Retry):
            process_sms_for_alert_group(alert_group.id, rule.id)
        retry_mock.assert_called_once()
