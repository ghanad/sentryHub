from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from integrations.models import SmsIntegrationRule, PhoneBook


class SmsRuleViewsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='tester', password='pass')
        self.client.login(username='tester', password='pass')
        PhoneBook.objects.create(name='alice', phone_number='09100000000')

    def test_list_view(self):
        SmsIntegrationRule.objects.create(name='r1', match_criteria={}, recipients='alice', firing_template='hi')
        SmsIntegrationRule.objects.create(name='r2', match_criteria={}, recipients='alice', firing_template='hi')
        resp = self.client.get(reverse('integrations:sms-rule-list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'r1')
        self.assertContains(resp, 'r2')
        self.assertContains(resp, reverse('integrations:sms-rule-create'))

    def test_create_view(self):
        resp = self.client.post(
            reverse('integrations:sms-rule-create'),
            {
                'name': 'new',
                'is_active': True,
                'priority': 0,
                'match_criteria': '{}',
                'recipients': 'alice',
                'use_sms_annotation': False,
                'firing_template': 'hi',
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(SmsIntegrationRule.objects.filter(name='new').exists())

    def test_update_view(self):
        rule = SmsIntegrationRule.objects.create(name='old', match_criteria={}, recipients='alice', firing_template='hi')
        resp = self.client.post(
            reverse('integrations:sms-rule-update', args=[rule.id]),
            {
                'name': 'updated',
                'is_active': True,
                'priority': 0,
                'match_criteria': '{}',
                'recipients': 'alice',
                'use_sms_annotation': False,
                'firing_template': 'hi2',
            },
        )
        self.assertEqual(resp.status_code, 302)
        rule.refresh_from_db()
        self.assertEqual(rule.name, 'updated')
        self.assertEqual(rule.firing_template, 'hi2')

    def test_delete_view(self):
        rule = SmsIntegrationRule.objects.create(name='del', match_criteria={}, recipients='alice', firing_template='hi')
        resp = self.client.post(reverse('integrations:sms-rule-delete', args=[rule.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(SmsIntegrationRule.objects.filter(id=rule.id).exists())

    def test_sms_rule_guide_view(self):
        # The guide file is expected to exist and contain the actual content.
        # We are not creating a temporary file here to avoid overwriting.
        resp = self.client.get(reverse('integrations:sms-rule-guide'))
        self.assertEqual(resp.status_code, 200)
        # Check for content that should be present in the actual guide
        self.assertContains(resp, "راهنمای تنظیم قوانین یکپارچه‌سازی پیامک (SMS) در SentryHub")
        self.assertContains(resp, "هدف اصلی این قوانین، تعریف <strong>شرایطی</strong> است")
