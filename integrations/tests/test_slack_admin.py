from django.test import TestCase
from django.contrib.admin.sites import AdminSite

from integrations.admin import SlackIntegrationRuleAdmin
from integrations.models import SlackIntegrationRule


class SlackIntegrationRuleAdminTests(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = SlackIntegrationRuleAdmin(SlackIntegrationRule, self.site)

    def test_list_display(self):
        self.assertEqual(
            self.admin.list_display,
            ('name', 'is_active', 'priority', 'slack_channel')
        )
