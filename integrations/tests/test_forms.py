from django.test import TestCase, override_settings

from integrations.forms import JiraIntegrationRuleForm

TEST_JIRA_CONFIG = {
    'allowed_project_keys': ['TEST'],
    'ISSUE_TYPE_CHOICES': [('Bug', 'Bug')],
}


@override_settings(JIRA_CONFIG=TEST_JIRA_CONFIG)
class JiraIntegrationRuleFormTests(TestCase):
    def get_valid_data(self, **overrides):
        data = {
            'name': 'Rule1',
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
        data.update(overrides)
        return data

    def test_clean_match_criteria_json_string(self):
        form = JiraIntegrationRuleForm(data=self.get_valid_data())
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['match_criteria'], {"severity": "critical"})

    def test_clean_match_criteria_invalid_json(self):
        form = JiraIntegrationRuleForm(data=self.get_valid_data(match_criteria='{invalid}'))
        self.assertFalse(form.is_valid())
        self.assertIn('match_criteria', form.errors)

    def test_clean_assignee_length(self):
        long_assignee = 'a' * 101
        form = JiraIntegrationRuleForm(data=self.get_valid_data(assignee=long_assignee))
        self.assertFalse(form.is_valid())
        self.assertIn('Ensure this value has at most 100 characters', form.errors['assignee'][0])

    def test_get_issue_types(self):
        form = JiraIntegrationRuleForm()
        self.assertEqual(form.get_issue_types(), [('Bug', 'Bug')])
