from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from alerts.models import AlertGroup
from integrations.models import PhoneBook, SmsIntegrationRule, SmsMessageLog


class SmsHistoryViewTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="viewer", password="pass123")
        self.client.login(username="viewer", password="pass123")
        self.alert_group = AlertGroup.objects.create(
            fingerprint="hist-fp",
            name="History Alert",
            labels={},
            source="prometheus",
        )
        self.rule = SmsIntegrationRule.objects.create(
            name="history-rule",
            match_criteria={},
            recipients="",
            firing_template="body",
        )

    def test_history_page_lists_logs(self):
        PhoneBook.objects.create(name="Ali", phone_number="0912")
        PhoneBook.objects.create(name="Sara", phone_number="0935")
        SmsMessageLog.objects.create(
            rule=self.rule,
            alert_group=self.alert_group,
            recipients=["0912", "0935"],
            message="Test message",
            delivery_method="HTTP",
            status=SmsMessageLog.STATUS_SUCCESS,
            provider_response={"messages": [{"status": 0}]},
        )

        response = self.client.get(reverse("integrations:sms-history"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SMS History")
        self.assertContains(response, "history-rule")
        self.assertContains(response, "Ali")
        self.assertContains(response, "Sara")
        self.assertNotContains(response, "Ali, Sara")
        self.assertContains(response, "HTTP")
        self.assertContains(response, "Success")

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("integrations:sms-history"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)
