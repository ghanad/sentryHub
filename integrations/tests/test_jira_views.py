from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from unittest.mock import patch, mock_open

from integrations.models import JiraIntegrationRule


class JiraRuleListViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user", password="pass")

    def _create_rule(self, name, priority=0, is_active=True):
        return JiraIntegrationRule.objects.create(
            name=name,
            match_criteria={"severity": "critical"},
            jira_project_key="OPS",
            jira_issue_type="Task",
            priority=priority,
            is_active=is_active,
        )

    def test_list_view_filters_and_context(self):
        active_rule = self._create_rule("ActiveRule", priority=5, is_active=True)
        inactive_rule = self._create_rule("InactiveRule", priority=1, is_active=False)

        self.client.login(username="user", password="pass")
        url = reverse("integrations:jira-rule-list")

        # No filters: both rules ordered by priority desc then name
        response = self.client.get(url)
        self.assertEqual(list(response.context["jira_rules"]), [active_rule, inactive_rule])
        self.assertEqual(response.context["active_filter"], "")
        self.assertIn("jira_rule_guide_content", response.context)
        self.assertTrue(response.context["jira_rule_guide_content"])

        # Filter active
        response_active = self.client.get(url, {"active": "true"})
        self.assertEqual(list(response_active.context["jira_rules"]), [active_rule])
        self.assertEqual(response_active.context["active_filter"], "true")

        # Filter inactive
        response_inactive = self.client.get(url, {"active": "false"})
        self.assertEqual(list(response_inactive.context["jira_rules"]), [inactive_rule])
        self.assertEqual(response_inactive.context["active_filter"], "false")


@override_settings(JIRA_CONFIG={'allowed_project_keys': ['OPS'], 'ISSUE_TYPE_CHOICES': [('Bug', 'Bug')]})
class JiraRuleCrudViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user", password="pass")

    def _valid_data(self, name="Rule1", assignee=""):
        return {
            'name': name,
            'is_active': 'on',
            'priority': 0,
            'jira_project_key': 'OPS',
            'jira_issue_type': 'Bug',
            'assignee': assignee,
            'jira_title_template': 't',
            'jira_description_template': 'd',
            'jira_update_comment_template': 'c',
            'match_criteria': '{}',
            'watchers': '',
        }

    def test_create_view_get(self):
        self.client.login(username="user", password="pass")
        response = self.client.get(reverse('integrations:jira-rule-create'))
        self.assertEqual(response.status_code, 200)

    def test_update_view_get(self):
        rule = JiraIntegrationRule.objects.create(name='Rule1', match_criteria={}, jira_project_key='OPS', jira_issue_type='Bug')
        self.client.login(username="user", password="pass")
        response = self.client.get(reverse('integrations:jira-rule-update', args=[rule.pk]))
        self.assertEqual(response.status_code, 200)

    def test_delete_view_removes_rule(self):
        rule = JiraIntegrationRule.objects.create(name='Rule1', match_criteria={}, jira_project_key='OPS', jira_issue_type='Bug')
        self.client.login(username="user", password="pass")
        response = self.client.post(
            reverse('integrations:jira-rule-delete', args=[rule.pk]),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(JiraIntegrationRule.objects.filter(pk=rule.pk).exists())


class JiraGuideViewTests(TestCase):
    @patch('integrations.views.open', new_callable=mock_open, read_data='guide content')
    def test_returns_file_content(self, m_open):
        user = User.objects.create_user(username="user", password="pass")
        self.client.login(username="user", password="pass")
        response = self.client.get(reverse('integrations:jira-rule-guide'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'guide content')


class JiraAdminViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user", password="pass")

    def test_requires_login(self):
        response = self.client.get(reverse('integrations:jira-admin'))
        self.assertEqual(response.status_code, 302)

    @patch('integrations.views.JiraService')
    def test_post_connection_test(self, mock_service_cls):
        mock_service = mock_service_cls.return_value
        mock_service.check_connection.return_value = True
        self.client.login(username="user", password="pass")
        response = self.client.post(reverse('integrations:jira-admin'), {'test_connection': '1'})
        self.assertEqual(response.status_code, 200)
        mock_service.check_connection.assert_called_once()
        self.assertTrue(response.context['connection_tested'])
        self.assertTrue(response.context['connection_successful'])

