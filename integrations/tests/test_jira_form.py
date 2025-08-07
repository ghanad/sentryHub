from django.test import TestCase, override_settings
from integrations.forms import JiraIntegrationRuleForm
from integrations.models import JiraIntegrationRule


@override_settings(JIRA_CONFIG={'allowed_project_keys': ['OPS'], 'ISSUE_TYPE_CHOICES': [('Bug', 'Bug')]})
class JiraIntegrationRuleFormTests(TestCase):
    def get_valid_data(self):
        return {
            'name': 'Rule1',
            'is_active': True,
            'priority': 0,
            'jira_project_key': 'OPS',
            'jira_issue_type': 'Bug',
            'assignee': 'alice',
            'jira_title_template': 'Title',
            'jira_description_template': 'Desc',
            'jira_update_comment_template': 'Comment',
            'match_criteria': '{"job": "node"}',
            'watchers': '',
        }

    def test_init_sets_project_key_and_issue_type_choices(self):
        form = JiraIntegrationRuleForm()
        self.assertEqual(form.fields['jira_project_key'].initial, 'OPS')
        self.assertEqual(form.fields['jira_project_key'].widget.attrs.get('readonly'), 'readonly')
        self.assertEqual(form.fields['jira_issue_type'].choices, [('Bug', 'Bug')])

    def test_clean_match_criteria_parses_json(self):
        data = self.get_valid_data()
        form = JiraIntegrationRuleForm(data=data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['match_criteria'], {'job': 'node'})

    def test_clean_match_criteria_accepts_dict(self):
        data = self.get_valid_data()
        data['match_criteria'] = {'job': 'node'}
        form = JiraIntegrationRuleForm(data=data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['match_criteria'], {'job': 'node'})

    def test_clean_match_criteria_invalid_json(self):
        data = self.get_valid_data()
        data['match_criteria'] = '{"job":'
        form = JiraIntegrationRuleForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('Enter a valid JSON.', form.errors['match_criteria'])

    def test_clean_validates_assignee_length(self):
        data = self.get_valid_data()
        data['assignee'] = 'a' * 101
        form = JiraIntegrationRuleForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('Ensure this value has at most 100 characters (it has 101).', form.errors['assignee'])

    def test_save_creates_rule(self):
        data = self.get_valid_data()
        form = JiraIntegrationRuleForm(data=data)
        self.assertTrue(form.is_valid())
        rule = form.save()
        self.assertIsInstance(rule, JiraIntegrationRule)
        self.assertEqual(rule.match_criteria, {'job': 'node'})
