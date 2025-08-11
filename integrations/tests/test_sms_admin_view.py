from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from unittest.mock import patch

from integrations.models import PhoneBook


class SmsAdminViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="u", password="p")
        self.client.force_login(self.user)
        self.url = reverse("integrations:sms-admin")

    @patch("integrations.views.SmsService.get_balance", return_value=123)
    def test_get_balance_displayed(self, mock_balance):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "123")

    @patch("integrations.views.SmsService.send_sms", return_value=True)
    @patch("integrations.views.SmsService.get_balance", return_value=0)
    def test_send_test_sms(self, mock_balance, mock_send):
        entry = PhoneBook.objects.create(name="ali", phone_number="09120000000")
        response = self.client.post(self.url, {"recipient": entry.id, "message": "hi"})
        self.assertEqual(response.status_code, 302)
        mock_send.assert_called_once_with("09120000000", "hi")
