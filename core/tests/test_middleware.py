from django.test import TestCase, RequestFactory
from unittest.mock import MagicMock
from django.contrib.auth import get_user_model
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.urls import reverse
from core.middleware import AdminAccessMiddleware

User = get_user_model()

class AdminAccessMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = AdminAccessMiddleware(lambda req: None) # Mock get_response
        self.admin_user = User.objects.create_user(username='admin', password='password', is_staff=True)
        self.normal_user = User.objects.create_user(username='normal', password='password', is_staff=False)
        self.admin_urls = ['/admin/', '/users/'] # Simplified list for testing

    def add_messages_and_session_to_request(self, request):
        """Helper to add session and message capabilities to a request."""
        SessionMiddleware(lambda req: None).process_request(request)
        request.session.save()
        MessageMiddleware(lambda req: None).process_request(request)
        return request

    def test_admin_access_authenticated_staff(self):
        """
        Staff user should be able to access admin URLs.
        """
        request = self.factory.get('/admin/')
        request.user = self.admin_user
        request = self.add_messages_and_session_to_request(request)

        response = self.middleware(request)
        self.assertIsNone(response) # Should not redirect, pass to next middleware

    def test_admin_access_authenticated_non_staff(self):
        """
        Non-staff authenticated user should be redirected from admin URLs.
        """
        self.client.login(username='normal', password='password')
        response = self.client.get('/admin/', follow=True) # Follow the redirect

        self.assertRedirects(response, reverse('login'))
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'You do not have permission to access this section.')

    def test_admin_access_unauthenticated(self):
        """
        Unauthenticated user should be redirected from admin URLs.
        """
        response = self.client.get('/users/', follow=True) # Follow the redirect

        self.assertRedirects(response, reverse('login'))
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'You do not have permission to access this section.')

    def test_non_admin_access_authenticated(self):
        """
        Authenticated user should be able to access non-admin URLs.
        """
        request = self.factory.get('/some-app-page/')
        request.user = self.normal_user
        request = self.add_messages_and_session_to_request(request)

        response = self.middleware(request)
        self.assertIsNone(response) # Should not redirect

    def test_non_admin_access_unauthenticated(self):
        """
        Unauthenticated user should be able to access non-admin URLs (middleware doesn't interfere).
        """
        request = self.factory.get('/some-public-page/')
        request.user = MagicMock(is_authenticated=False)
        request = self.add_messages_and_session_to_request(request)

        response = self.middleware(request)
        self.assertIsNone(response) # Should not redirect