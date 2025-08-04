from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from unittest.mock import patch

class SlackAdminViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='tester', password='pass')

    def test_requires_login(self):
        response = self.client.get(reverse('integrations:slack-admin'))
        self.assertEqual(response.status_code, 302)  # redirect to login

    def test_get_page(self):
        self.client.login(username='tester', password='pass')
        response = self.client.get(reverse('integrations:slack-admin'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Send Test Message')

    @patch('integrations.views.SlackService')
    def test_post_sends_message(self, mock_service_cls):
        mock_service = mock_service_cls.return_value
        mock_service.send_notification.return_value = True
        self.client.login(username='tester', password='pass')
        response = self.client.post(
            reverse('integrations:slack-admin'),
            {'channel': 'channel', 'message': 'hello'},
        )
        self.assertEqual(response.status_code, 200)
        mock_service.send_notification.assert_called_once_with('channel', 'hello')

