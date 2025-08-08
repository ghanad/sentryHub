from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from unittest.mock import patch, mock_open
import markdown


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
            {'channel': 'channel', 'message': 'hello', 'send_simple': '1'},
        )
        self.assertEqual(response.status_code, 200)
        mock_service.send_notification.assert_called_once_with('channel', 'hello')


class SlackAdminGuideViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='tester', password='pass')

    def test_requires_login(self):
        resp = self.client.get(reverse('integrations:slack-admin-guide'))
        self.assertEqual(resp.status_code, 302)

    @patch('integrations.views.open', new_callable=mock_open, read_data='# Title')
    @patch('integrations.views.markdown.markdown', side_effect=markdown.markdown)
    def test_renders_guide_content(self, md_mock, open_mock):
        self.client.login(username='tester', password='pass')
        resp = self.client.get(reverse('integrations:slack-admin-guide'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Title')
        open_mock.assert_called_once()
