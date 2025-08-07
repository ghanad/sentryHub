from django.core.exceptions import ValidationError
from django.test import TestCase
from integrations.models import JiraIntegrationRule


class JiraIntegrationRuleModelTests(TestCase):
    def create_rule(self, **kwargs):
        data = {
            'name': 'Rule1',
            'is_active': True,
            'match_criteria': {'job': 'node'},
            'jira_project_key': 'OPS',
            'jira_issue_type': 'Bug',
            'assignee': '',
            'jira_title_template': 'Title',
            'jira_description_template': 'Desc',
            'jira_update_comment_template': 'Comment',
            'priority': 0,
            'watchers': '',
        }
        data.update(kwargs)
        return JiraIntegrationRule.objects.create(**data)

    def test_str_and_get_assignee(self):
        rule = self.create_rule(priority=5, assignee='')
        self.assertEqual(str(rule), 'Rule1 (Active, Prio: 5)')
        self.assertIsNone(rule.get_assignee())

        rule_with_assignee = self.create_rule(name='Rule2', assignee='alice')
        self.assertEqual(rule_with_assignee.get_assignee(), 'alice')

    def test_clean_invalid_match_criteria(self):
        rule = JiraIntegrationRule(
            name='Invalid',
            is_active=True,
            match_criteria='not a dict',
            jira_project_key='OPS',
            jira_issue_type='Bug',
            assignee='',
            jira_title_template='Title',
            jira_description_template='Desc',
            jira_update_comment_template='Comment',
            priority=0,
            watchers='',
        )
        with self.assertRaises(ValidationError):
            rule.full_clean()

    def test_ordering(self):
        self.create_rule(name='B', priority=5)
        self.create_rule(name='A', priority=5)
        self.create_rule(name='C', priority=3)

        names = list(JiraIntegrationRule.objects.values_list('name', flat=True))
        self.assertEqual(names, ['A', 'B', 'C'])
