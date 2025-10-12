from datetime import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from alerts.models import AlertGroup
from integrations.models import PhoneBook, SmsIntegrationRule, SmsMessageLog
from core.templatetags.date_format_tags import force_jalali
from users.models import UserProfile


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
            provider_response={"messages": [{"status": 0}, {"status": 1}]},
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
        self.assertContains(response, "Sent successfully")
        self.assertContains(response, "Invalid recipient number")

        rows = response.context["sms_log_rows"]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["recipient_display"], "Ali")
        self.assertEqual(rows[0]["provider_status_display"], "Sent successfully")
        self.assertEqual(rows[1]["recipient_display"], "Sara")
        self.assertEqual(rows[1]["provider_status_display"], "Invalid recipient number")

    def test_sent_at_uses_user_date_preference(self):
        profile, _ = UserProfile.objects.get_or_create(user=self.user)
        profile.date_format_preference = "jalali"
        profile.save()

        fixed_time = timezone.make_aware(datetime(2024, 5, 5, 12, 45))

        log = SmsMessageLog.objects.create(
            rule=self.rule,
            alert_group=self.alert_group,
            recipients=["0912"],
            message="Time test",
            delivery_method="HTTP",
            status=SmsMessageLog.STATUS_SUCCESS,
            provider_response={"messages": [{"status": 0}]},
        )
        SmsMessageLog.objects.filter(pk=log.pk).update(created_at=fixed_time)

        response = self.client.get(reverse("integrations:sms-history"))
        self.assertEqual(response.status_code, 200)

        expected_display = force_jalali(fixed_time, "%Y-%m-%d %H:%M")
        self.assertContains(response, expected_display)

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("integrations:sms-history"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)
