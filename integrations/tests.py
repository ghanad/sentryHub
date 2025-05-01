# integrations/tests.py
from django.test import TestCase
from django.core.exceptions import ValidationError
from integrations.models import JiraIntegrationRule

class JiraIntegrationRuleModelTests(TestCase):

    def test_create_jira_integration_rule(self):
        """
        Test creating a basic JiraIntegrationRule instance.
        """
        rule = JiraIntegrationRule.objects.create(
            name="Test Rule 1",
            match_criteria={"severity": "critical"},
            jira_project_key="TEST",
            jira_issue_type="Bug",
            jira_title_template="Alert: {{ alertname }}",
            jira_description_template="Details: {{ labels }}"
        )
        self.assertEqual(rule.name, "Test Rule 1")
        self.assertEqual(rule.match_criteria, {"severity": "critical"})
        self.assertEqual(rule.jira_project_key, "TEST")
        self.assertEqual(rule.jira_issue_type, "Bug")
        self.assertTrue(rule.is_active) # Check default is_active
        self.assertEqual(rule.priority, 0) # Check default priority
        self.assertEqual(rule.watchers, "") # Check default watchers
        self.assertEqual(rule.assignee, "") # Check default assignee

    def test_match_criteria_default(self):
        """
        Test that match_criteria defaults to an empty dictionary.
        """
        rule = JiraIntegrationRule.objects.create(
            name="Test Rule With Default Match Criteria",
            jira_project_key="TEST",
            jira_issue_type="Task"
        )
        self.assertEqual(rule.match_criteria, {})

    def test_clean_method_valid_match_criteria(self):
        """
        Test that the clean method passes with valid dictionary match_criteria.
        """
        rule = JiraIntegrationRule(
            name="Test Rule Clean Valid",
            match_criteria={"job": "node_exporter"},
            jira_project_key="TEST",
            jira_issue_type="Bug"
        )
        try:
            rule.full_clean()
        except ValidationError:
            self.fail("full_clean raised ValidationError unexpectedly!")

    def test_clean_method_invalid_match_criteria(self):
        """
        Test that the clean method raises ValidationError for invalid match_criteria.
        """
        rule = JiraIntegrationRule(
            name="Test Rule Clean Invalid",
            match_criteria="not a dictionary", # Invalid data
            jira_project_key="TEST",
            jira_issue_type="Bug"
        )
        with self.assertRaises(ValidationError) as cm:
            rule.full_clean()
        self.assertIn('match_criteria', cm.exception.message_dict)
        self.assertIn('Must be a valid JSON object (dictionary).', cm.exception.message_dict['match_criteria'])

    def test_str_representation_active(self):
        """
        Test the __str__ method for an active rule.
        """
        rule = JiraIntegrationRule.objects.create(
            name="Active Rule",
            is_active=True,
            jira_project_key="TEST",
            jira_issue_type="Task"
        )
        self.assertEqual(str(rule), "Active Rule (Active, Prio: 0)")

    def test_str_representation_inactive(self):
        """
        Test the __str__ method for an inactive rule.
        """
        rule = JiraIntegrationRule.objects.create(
            name="Inactive Rule",
            is_active=False,
            jira_project_key="TEST",
            jira_issue_type="Task",
            priority=10
        )
        self.assertEqual(str(rule), "Inactive Rule (Inactive, Prio: 10)")

    def test_get_assignee_with_assignee(self):
        """
        Test get_assignee method when assignee is set.
        """
        rule = JiraIntegrationRule.objects.create(
            name="Rule with Assignee",
            jira_project_key="TEST",
            jira_issue_type="Task",
            assignee="testuser"
        )
        self.assertEqual(rule.get_assignee(), "testuser")

    def test_get_assignee_without_assignee(self):
        """
        Test get_assignee method when assignee is not set.
        """
        rule = JiraIntegrationRule.objects.create(
            name="Rule without Assignee",
            jira_project_key="TEST",
            jira_issue_type="Task",
            assignee="" # Explicitly empty
        )
        self.assertIsNone(rule.get_assignee())

        rule_no_assignee_field = JiraIntegrationRule.objects.create(
            name="Rule without Assignee Field",
            jira_project_key="TEST",
            jira_issue_type="Task"
            # Assignee field is not provided, defaults to blank
        )
        self.assertIsNone(rule_no_assignee_field.get_assignee())
