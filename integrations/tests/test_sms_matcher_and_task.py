from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from alerts.models import AlertGroup
from integrations.models import PhoneBook, SmsIntegrationRule, SmsMessageLog
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
        nums, _ = matcher.resolve_recipients(self.alert_group, rule)
        self.assertEqual(set(nums), {'1', '2'})

    def test_rule_recipients_fallback(self):
        PhoneBook.objects.create(name='alice', phone_number='1')
        rule = SmsIntegrationRule.objects.create(name='r', match_criteria={}, recipients='alice', firing_template='hi')
        matcher = SmsRuleMatcherService()
        nums, should = matcher.resolve_recipients(self.alert_group, rule)
        self.assertEqual(nums, ['1'])
        self.assertFalse(should)

    def test_inactive_phonebook_entries_are_skipped(self):
        PhoneBook.objects.create(name='alice', phone_number='1', is_active=False)
        rule = SmsIntegrationRule.objects.create(name='r_inactive', match_criteria={}, recipients='alice', firing_template='hi')
        matcher = SmsRuleMatcherService()
        nums, should = matcher.resolve_recipients(self.alert_group, rule)
        self.assertEqual(nums, [])
        self.assertFalse(should)


    def test_case_insensitive_recipient_matching(self):
        PhoneBook.objects.create(name='Ali', phone_number='3')
        self.alert_group.instances.create(status='firing', started_at=timezone.now(), annotations={'sms': 'ali'})
        rule = SmsIntegrationRule.objects.create(name='r_case_insensitive', match_criteria={}, use_sms_annotation=True, firing_template='hi')
        matcher = SmsRuleMatcherService()
        nums, _ = matcher.resolve_recipients(self.alert_group, rule)
        self.assertEqual(set(nums), {'3'})


class SmsTaskTests(TestCase):
    @patch('integrations.tasks.SmsService')
    def test_process_sms_for_alert_group(self, service_cls):
        mock_service = service_cls.return_value
        mock_service.send_bulk.return_value = {"messages": [{"status": 1}]}
        PhoneBook.objects.create(name='alice', phone_number='1')
        alert_group = AlertGroup.objects.create(fingerprint='fp2', name='AG2', labels={}, source='prometheus')
        rule = SmsIntegrationRule.objects.create(name='r', match_criteria={}, recipients='alice', firing_template='msg')
        process_sms_for_alert_group.request.id = 'test'
        with self.assertLogs('integrations.tasks', level='INFO') as cm:
            process_sms_for_alert_group.run(alert_group.id, rule.id)
        mock_service.send_bulk.assert_called_once_with(['1'], 'msg', fingerprint='fp2')
        log_output = ' '.join(cm.output)
        self.assertIn('Message body: msg', log_output)
        self.assertIn('(FP: fp2)', log_output)
        self.assertEqual(SmsMessageLog.objects.count(), 1)
        sms_log = SmsMessageLog.objects.first()
        self.assertEqual(sms_log.status, SmsMessageLog.STATUS_SUCCESS)
        self.assertEqual(sms_log.rule, rule)
        self.assertEqual(sms_log.alert_group, alert_group)
        self.assertEqual(sms_log.recipients, ['1'])

    @patch('integrations.tasks.SmsService')
    def test_sms_template_with_summary(self, service_cls):
        mock_service = service_cls.return_value
        mock_service.send_bulk.return_value = {"messages": [{"status": 1}]}
        PhoneBook.objects.create(name='test_user', phone_number='1234567890')
        
        alert_group = AlertGroup.objects.create(
            fingerprint='fp_summary',
            name='Test Alert Group',
            labels={'env': 'dev'},
            source='test'
        )
        alert_group.instances.create(
            status='firing',
            started_at=timezone.now(),
            annotations={'summary': 'This is a test summary.'}
        )
        
        rule = SmsIntegrationRule.objects.create(
            name='summary_rule',
            match_criteria={},
            recipients='test_user',
            firing_template='Alert: {{ alert_group.name }}. Summary: {{ summary }}'
        )
        
        process_sms_for_alert_group.request.id = 'test_summary_task'
        with self.assertLogs('integrations.tasks', level='INFO') as cm:
            process_sms_for_alert_group.run(alert_group.id, rule.id)

        expected_message = 'Alert: Test Alert Group. Summary: This is a test summary.'
        mock_service.send_bulk.assert_called_once_with(['1234567890'], expected_message, fingerprint='fp_summary')
        log_output = ' '.join(cm.output)
        self.assertIn(f'Message body: {expected_message}', log_output)
        self.assertIn('(FP: fp_summary)', log_output)
        self.assertEqual(SmsMessageLog.objects.count(), 1)
        sms_log = SmsMessageLog.objects.first()
        self.assertEqual(sms_log.message, expected_message)
        self.assertEqual(sms_log.status, SmsMessageLog.STATUS_SUCCESS)

    @patch('integrations.tasks.SmsService')
    @patch('integrations.tasks.process_sms_for_alert_group.retry', side_effect=Retry('boom'))
    def test_task_retries_on_error(self, retry_mock, service_cls):
        service_cls.return_value.send_bulk.side_effect = SmsNotificationError('net')
        PhoneBook.objects.create(name='alice', phone_number='1')
        alert_group = AlertGroup.objects.create(fingerprint='fp3', name='AG3', labels={}, source='prometheus')
        rule = SmsIntegrationRule.objects.create(name='r', match_criteria={}, recipients='alice', firing_template='msg')
        process_sms_for_alert_group.app.conf.update(task_always_eager=True, task_store_eager_result=False, task_eager_propagates=True, result_backend='cache+memory://')
        with self.assertRaises(Retry):
            process_sms_for_alert_group.apply(args=(alert_group.id, rule.id))
        retry_mock.assert_called_once()
        self.assertEqual(SmsMessageLog.objects.count(), 1)
        failure_log = SmsMessageLog.objects.first()
        self.assertEqual(failure_log.status, SmsMessageLog.STATUS_FAILED)
        self.assertEqual(failure_log.error_message, 'net')
