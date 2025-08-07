from django.core.exceptions import ValidationError
from django.test import TestCase

from integrations.models import JiraIntegrationRule


class JiraIntegrationRuleModelTests(TestCase):
    def test_str_and_get_assignee(self):
        rule = JiraIntegrationRule.objects.create(
            name="Rule1",
            match_criteria={"severity": "critical"},
            jira_project_key="TEST",
            jira_issue_type="Bug",
            assignee=""
        )
        self.assertEqual(str(rule), "Rule1 (Active, Prio: 0)")
        self.assertIsNone(rule.get_assignee())
        rule.assignee = "alice"
        self.assertEqual(rule.get_assignee(), "alice")

    def test_clean_invalid_match_criteria(self):
        rule = JiraIntegrationRule(
            name="BadRule",
            match_criteria="not_a_dict",
            jira_project_key="TEST",
            jira_issue_type="Bug",
        )
        with self.assertRaises(ValidationError):
            rule.clean()
