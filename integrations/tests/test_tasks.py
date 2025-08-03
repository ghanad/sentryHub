from unittest.mock import MagicMock, patch
from django.test import TestCase, override_settings

from integrations.tasks import render_template_safe
import integrations.tasks as task_module

TEST_JIRA_CONFIG = {
    'open_status_categories': ['To Do'],
    'closed_status_categories': ['Done'],
}

@override_settings(JIRA_CONFIG=TEST_JIRA_CONFIG)
class JiraTaskTests(TestCase):
    def test_render_template_safe(self):
        template = 'Hello {{ name }}'
        context = {'name': 'World'}
        self.assertEqual(render_template_safe(template, context, 'default'), 'Hello World')
        self.assertEqual(render_template_safe('', context, 'default'), 'default')

    @patch('integrations.tasks.JiraService')
    @patch('integrations.tasks.JiraIntegrationRule')
    @patch('integrations.tasks.AlertGroup')
    def test_process_jira_for_alert_group_client_none(self, mock_alert_group, mock_rule, mock_service):
        mock_service.return_value.client = None
        mock_alert_group.objects.get.return_value = MagicMock(
            fingerprint='fp',
            labels={},
            instances=MagicMock(order_by=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))),
            is_silenced=False,
            jira_issue_key=None,
            last_occurrence=None,
        )
        mock_rule.objects.get.return_value = MagicMock(jira_update_comment_template='')
        task_module.self = MagicMock(request=MagicMock(id='1'))
        result = task_module.process_jira_for_alert_group.__wrapped__(1, 1, 'firing')
        self.assertIsNone(result)
