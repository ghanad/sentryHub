from django.core.exceptions import ValidationError
from django.test import TestCase
from integrations.forms import SlackIntegrationRuleForm


class SlackIntegrationRuleFormTests(TestCase):
    def test_accepts_json_string_for_match_criteria(self):
        form = SlackIntegrationRuleForm(data={
            'name': 'r1',
            'is_active': True,
            'priority': 0,
            'match_criteria': '{"labels__env": "prod"}',
            'slack_channel': '#ops',
            'message_template': 'hello',
        })
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['match_criteria'], {'labels__env': 'prod'})

    def test_invalid_json_in_match_criteria(self):
        form = SlackIntegrationRuleForm(data={
            'name': 'r2',
            'is_active': True,
            'priority': 0,
            'match_criteria': '{invalid json}',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('match_criteria', form.errors)

    def test_optional_fields_and_default_priority(self):
        form = SlackIntegrationRuleForm(data={'name': 'r3', 'is_active': True, 'priority': 0, 'match_criteria': '{}'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['match_criteria'], {})
        self.assertEqual(form.cleaned_data['slack_channel'], '')
        self.assertEqual(form.cleaned_data['priority'], 0)
