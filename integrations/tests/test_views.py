from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from unittest.mock import patch

from integrations.models import JiraIntegrationRule

TEST_JIRA_CONFIG = {
    'allowed_project_keys': ['TEST'],
    'ISSUE_TYPE_CHOICES': [('Bug', 'Bug')],
    'test_project_key': 'TEST',
    'test_issue_type': 'Bug',
}

@override_settings(JIRA_CONFIG=TEST_JIRA_CONFIG)
class JiraRuleViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user', password='pass')
        self.client.login(username='user', password='pass')

    def create_rule(self, **kwargs):
        defaults = {
            'name': 'Rule1',
            'match_criteria': {"severity": "critical"},
            'jira_project_key': 'TEST',
            'jira_issue_type': 'Bug',
        }
        defaults.update(kwargs)
        return JiraIntegrationRule.objects.create(**defaults)

    def test_list_view(self):
        rule = self.create_rule()
        response = self.client.get(reverse('integrations:jira-rule-list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, rule.name)
        self.assertIn('jira_rule_guide_content', response.context)

    def test_create_view(self):
        data = {
            'name': 'RuleCreate',
            'is_active': True,
            'priority': 0,
            'jira_project_key': 'TEST',
            'jira_issue_type': 'Bug',
            'assignee': '',
            'jira_title_template': '',
            'jira_description_template': '',
            'jira_update_comment_template': '',
            'match_criteria': '{"severity": "critical"}',
            'watchers': '',
        }
        response = self.client.post(reverse('integrations:jira-rule-create'), data)
        self.assertRedirects(response, reverse('integrations:jira-rule-list'))
        self.assertTrue(JiraIntegrationRule.objects.filter(name='RuleCreate').exists())

    def test_update_view(self):
        rule = self.create_rule()
        data = {
            'name': 'Updated',
            'is_active': False,
            'priority': 1,
            'jira_project_key': 'TEST',
            'jira_issue_type': 'Bug',
            'assignee': '',
            'jira_title_template': '',
            'jira_description_template': '',
            'jira_update_comment_template': '',
            'match_criteria': '{"severity": "critical"}',
            'watchers': '',
        }
        response = self.client.post(reverse('integrations:jira-rule-update', args=[rule.pk]), data)
        self.assertRedirects(response, reverse('integrations:jira-rule-list'))
        rule.refresh_from_db()
        self.assertEqual(rule.name, 'Updated')
        self.assertFalse(rule.is_active)

    def test_delete_view(self):
        rule = self.create_rule()
        response = self.client.post(reverse('integrations:jira-rule-delete', args=[rule.pk]))
        self.assertRedirects(response, reverse('integrations:jira-rule-list'))
        self.assertFalse(JiraIntegrationRule.objects.filter(pk=rule.pk).exists())

    @patch('integrations.views.JiraService')
    def test_jira_admin_view_connection(self, mock_service):
        mock_service.return_value.check_connection.return_value = True
        response = self.client.post(reverse('integrations:jira-admin'), {'test_connection': ''})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Successfully connected')

    def test_jira_rule_guide_view(self):
        response = self.client.get(reverse('integrations:jira-rule-guide'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('guide_content_md', response.context)
