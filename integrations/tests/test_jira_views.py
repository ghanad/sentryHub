from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

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

