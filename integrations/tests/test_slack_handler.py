from unittest.mock import patch
from django.test import TestCase

from alerts.models import AlertGroup
from alerts.signals import alert_processed
from integrations.models import SlackIntegrationRule


class HandleAlertProcessedSlackTests(TestCase):
    def setUp(self):
        self.alert_group = AlertGroup.objects.create(
            fingerprint='fp',
            name='AG',
            labels={},
            source='prometheus',
        )
        self.rule = SlackIntegrationRule.objects.create(
            name='rule',
            slack_channel='#c',
            match_criteria={},
        )

    @patch('integrations.handlers.transaction.on_commit')
    @patch('integrations.handlers.process_slack_for_alert_group.delay')
    @patch('integrations.handlers.SlackRuleMatcherService')
    def test_triggers_task_when_rule_matches(self, matcher_mock, delay_mock, on_commit_mock):
        matcher_mock.return_value.find_matching_rule.return_value = self.rule
        alert_processed.send(sender=None, alert_group=self.alert_group, instance=None, status='firing')
        on_commit_mock.assert_called_once()
        callback = on_commit_mock.call_args[0][0]
        callback()
        delay_mock.assert_called_once_with(alert_group_id=self.alert_group.id, rule_id=self.rule.id)

    @patch('integrations.handlers.transaction.on_commit')
    @patch('integrations.handlers.process_slack_for_alert_group.delay')
    def test_skips_when_silenced(self, delay_mock, on_commit_mock):
        self.alert_group.is_silenced = True
        self.alert_group.save()
        alert_processed.send(sender=None, alert_group=self.alert_group, instance=None, status='firing')
        on_commit_mock.assert_not_called()
        delay_mock.assert_not_called()

    @patch('integrations.handlers.transaction.on_commit')
    @patch('integrations.handlers.process_slack_for_alert_group.delay')
    @patch('integrations.handlers.SlackRuleMatcherService')
    def test_skips_for_non_firing_or_resolved(self, matcher_mock, delay_mock, on_commit_mock):
        matcher_mock.return_value.find_matching_rule.return_value = self.rule
        alert_processed.send(sender=None, alert_group=self.alert_group, instance=None, status='pending')
        on_commit_mock.assert_not_called()
        delay_mock.assert_not_called()

    @patch('integrations.handlers.transaction.on_commit')
    @patch('integrations.handlers.process_slack_for_alert_group.delay')
    @patch('integrations.handlers.SlackRuleMatcherService')
    def test_logs_include_fingerprint(self, matcher_mock, delay_mock, on_commit_mock):
        matcher_mock.return_value.find_matching_rule.return_value = self.rule
        with self.assertLogs('integrations.handlers', level='INFO') as cm:
            alert_processed.send(sender=None, alert_group=self.alert_group, instance=None, status='firing')
        log_output = ' '.join(cm.output)
        self.assertIn(f"(FP: {self.alert_group.fingerprint})", log_output)
        on_commit_mock.assert_called_once()
        callback = on_commit_mock.call_args[0][0]
        callback()
        delay_mock.assert_called_once_with(alert_group_id=self.alert_group.id, rule_id=self.rule.id)
