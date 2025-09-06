from unittest.mock import patch, MagicMock
from django.test import TestCase
from alerts.models import AlertGroup
from alerts.signals import alert_processed
from integrations.models import PhoneBook, SmsIntegrationRule


class HandleAlertProcessedSmsTests(TestCase):
    def setUp(self):
        self.alert_group = AlertGroup.objects.create(
            fingerprint='fp',
            name='AG',
            labels={},
            source='prometheus',
        )
        PhoneBook.objects.create(name='alice', phone_number='1')
        self.rule = SmsIntegrationRule.objects.create(
            name='rule',
            match_criteria={},
            recipients='alice',
            firing_template='hi',
        )

    @patch('integrations.handlers.transaction')
    @patch('integrations.handlers.process_sms_for_alert_group')
    @patch('integrations.handlers.SmsRuleMatcherService')
    def test_triggers_task_when_rule_matches(self, matcher_mock, mock_task, mock_transaction):
        matcher_mock.return_value.find_matching_rule.return_value = self.rule
        mock_transaction.on_commit.side_effect = lambda func: func()

        alert_processed.send(sender=None, alert_group=self.alert_group, instance=None, status='firing')

        mock_transaction.on_commit.assert_called_once()
        mock_task.delay.assert_called_once_with(alert_group_id=self.alert_group.id, rule_id=self.rule.id)

    @patch('integrations.handlers.transaction')
    @patch('integrations.handlers.process_sms_for_alert_group')
    def test_skips_when_silenced(self, mock_task, mock_transaction):
        self.alert_group.is_silenced = True
        self.alert_group.save()
        alert_processed.send(sender=None, alert_group=self.alert_group, instance=None, status='firing')
        mock_transaction.on_commit.assert_not_called()
        mock_task.delay.assert_not_called()

    @patch('integrations.handlers.transaction')
    @patch('integrations.handlers.process_sms_for_alert_group')
    @patch('integrations.handlers.SmsRuleMatcherService')
    def test_skips_for_non_firing_or_resolved(self, matcher_mock, mock_task, mock_transaction):
        matcher_mock.return_value.find_matching_rule.return_value = self.rule
        alert_processed.send(sender=None, alert_group=self.alert_group, instance=None, status='pending')
        mock_transaction.on_commit.assert_not_called()
        mock_task.delay.assert_not_called()
