from django.test import TestCase
from integrations.forms import SmsIntegrationRuleForm


class SmsIntegrationRuleFormTests(TestCase):
    def test_valid_form(self):
        form = SmsIntegrationRuleForm(data={
            'name': 'r1',
            'is_active': True,
            'priority': 0,
            'match_criteria': '{}',
            'recipients': '',
            'use_sms_annotation': False,
            'firing_template': 'hi',
            'resolved_template': '',
        })
        self.assertTrue(form.is_valid())

    def test_invalid_json(self):
        form = SmsIntegrationRuleForm(data={
            'name': 'r1',
            'is_active': True,
            'priority': 0,
            'match_criteria': 'no',
            'firing_template': 'hi',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('match_criteria', form.errors)
