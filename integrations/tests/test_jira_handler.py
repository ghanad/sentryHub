from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch, MagicMock

from alerts.models import AlertGroup, AlertInstance
from integrations.models import JiraIntegrationRule
from integrations.handlers import handle_alert_processed


class HandleAlertProcessedTests(TestCase):
    def setUp(self):
        self.alert_group = AlertGroup.objects.create(
            fingerprint='fp1',
            name='AG',
            labels={'env': 'prod'},
            source='prometheus',
        )
        self.instance = AlertInstance.objects.create(
            alert_group=self.alert_group,
            status='firing',
            started_at=timezone.now(),
            annotations={},
        )

    @patch('integrations.handlers.transaction')
    @patch('integrations.handlers.process_jira_for_alert_group')
    @patch('integrations.handlers.JiraRuleMatcherService')
    def test_triggers_task_when_rule_matches(self, mock_matcher_cls, mock_task, mock_transaction):
        rule = JiraIntegrationRule.objects.create(
            name='Rule',
            match_criteria={},
            jira_project_key='OPS',
            jira_issue_type='Bug',
        )
        mock_matcher = mock_matcher_cls.return_value
        mock_matcher.find_matching_rule.return_value = rule

        # Mock on_commit to immediately execute the passed function
        mock_transaction.on_commit.side_effect = lambda func: func()

        handle_alert_processed(
            sender=None,
            alert_group=self.alert_group,
            status='firing',
            instance=self.instance,
        )

        mock_matcher.find_matching_rule.assert_called_once_with(self.alert_group.labels)
        mock_transaction.on_commit.assert_called_once()

        mock_task.delay.assert_called_once_with(
            alert_group_id=self.alert_group.id,
            rule_id=rule.id,
            alert_status='firing',
            triggering_instance_id=self.instance.id,
            fingerprint=self.alert_group.fingerprint,
        )

