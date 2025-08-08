from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from integrations.models import SlackIntegrationRule


class SlackRuleViewsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='tester', password='pass')
        self.client.login(username='tester', password='pass')

    def test_list_view(self):
        SlackIntegrationRule.objects.create(name='r1', slack_channel='#a', match_criteria={})
        SlackIntegrationRule.objects.create(name='r2', slack_channel='#b', match_criteria={})
        resp = self.client.get(reverse('integrations:slack-rule-list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'r1')
        self.assertContains(resp, 'r2')

    def test_create_view(self):
        resp = self.client.post(
            reverse('integrations:slack-rule-create'),
            {
                'name': 'new',
                'is_active': True,
                'priority': 0,
                'match_criteria': '{}',
                'slack_channel': '#chan',
                'message_template': 'hi',
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(SlackIntegrationRule.objects.filter(name='new').exists())

    def test_update_view(self):
        rule = SlackIntegrationRule.objects.create(name='old', slack_channel='#a', match_criteria={})
        resp = self.client.post(
            reverse('integrations:slack-rule-update', args=[rule.id]),
            {
                'name': 'updated',
                'is_active': True,
                'priority': 0,
                'match_criteria': '{}',
                'slack_channel': '#b',
                'message_template': '',
            },
        )
        self.assertEqual(resp.status_code, 302)
        rule.refresh_from_db()
        self.assertEqual(rule.name, 'updated')
        self.assertEqual(rule.slack_channel, '#b')

    def test_delete_view(self):
        rule = SlackIntegrationRule.objects.create(name='del', slack_channel='#a', match_criteria={})
        resp = self.client.post(reverse('integrations:slack-rule-delete', args=[rule.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(SlackIntegrationRule.objects.filter(id=rule.id).exists())
