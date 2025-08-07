from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone

from integrations.handlers import handle_alert_processed
from integrations.models import JiraIntegrationRule
from alerts.models import AlertGroup, AlertInstance


class HandleAlertProcessedTests(TestCase):
    def setUp(self):
        self.rule = JiraIntegrationRule.objects.create(
            name='Rule1',
            match_criteria={'severity': 'critical'},
            jira_project_key='TEST',
            jira_issue_type='Bug'
        )
        self.alert_group = AlertGroup.objects.create(
            fingerprint='fp1',
            name='Alert1',
            labels={'severity': 'critical'},
            severity='critical'
        )
        self.alert_instance = AlertInstance.objects.create(
            alert_group=self.alert_group,
            status='firing',
            started_at=timezone.now(),
            annotations={}
        )

    @patch('integrations.handlers.process_jira_for_alert_group')
    @patch('integrations.handlers.JiraRuleMatcherService')
    def test_firing_triggers_task(self, mock_matcher, mock_task):
        mock_matcher.return_value.find_matching_rule.return_value = self.rule
        handle_alert_processed(
            sender=None,
            alert_group=self.alert_group,
            status='firing',
            instance=self.alert_instance
        )
        mock_task.delay.assert_called_once_with(
            alert_group_id=self.alert_group.id,
            rule_id=self.rule.id,
            alert_status='firing',
            triggering_instance_id=self.alert_instance.id
        )

    @patch('integrations.handlers.process_jira_for_alert_group')
    @patch('integrations.handlers.JiraRuleMatcherService')
    def test_silenced_does_not_trigger(self, mock_matcher, mock_task):
        self.alert_group.is_silenced = True
        self.alert_group.save()
        handle_alert_processed(
            sender=None,
            alert_group=self.alert_group,
            status='firing',
            instance=self.alert_instance
        )
        mock_task.delay.assert_not_called()
