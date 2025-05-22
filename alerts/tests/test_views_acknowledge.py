# alerts/tests/test_views_acknowledge.py

import unittest
from unittest.mock import patch, MagicMock
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware

# Import the view function and service function
from alerts.views import acknowledge_alert_from_list
from alerts.models import AlertGroup # Will be mocked
from alerts.services.alerts_processor import acknowledge_alert # Will be mocked

class AcknowledgeAlertFromListViewTests(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.alert_group = MagicMock(spec=AlertGroup)
        self.alert_group.fingerprint = 'test_fingerprint'
        self.alert_group.name = 'Test Alert'
        self.alert_group.acknowledged = False # Default to not acknowledged

        # Apply session and message middleware to requests
        self.session_middleware = SessionMiddleware(lambda req: None)
        self.message_middleware = MessageMiddleware(lambda req: None)

    def process_request_with_middleware(self, request):
        # Apply session middleware
        self.session_middleware.process_request(request)
        # Apply message middleware
        self.message_middleware.process_request(request)
        return request

    @patch('alerts.views.get_object_or_404')
    @patch('alerts.views.acknowledge_alert')
    @patch('alerts.views.messages')
    def test_acknowledge_success(self, mock_messages, mock_acknowledge_alert, mock_get_object_or_404):
        """Test successful acknowledgement with valid data."""
        mock_get_object_or_404.return_value = self.alert_group

        request = self.factory.post(reverse('alerts:acknowledge-alert-from-list'), {
            'fingerprint': 'test_fingerprint',
            'comment': 'Test comment for acknowledgement',
            'next': '/alerts/?status=firing' # Simulate next URL
        })
        request.user = self.user
        request = self.process_request_with_middleware(request)

        response = acknowledge_alert_from_list(request)

        mock_get_object_or_404.assert_called_once_with(AlertGroup, fingerprint='test_fingerprint')
        mock_acknowledge_alert.assert_called_once_with(self.alert_group, self.user, 'Test comment for acknowledgement')
        mock_messages.success.assert_called_once_with(request, "Alert 'Test Alert' acknowledged successfully.")
        self.assertIsInstance(response, HttpResponseRedirect)
        # The view redirects to the alert list, preserving GET parameters from the original request URL.
        # Since the original request URL for this test had no GET parameters, it should redirect to the base list URL.
        self.assertEqual(response.url, reverse('alerts:alert-list'))

    @patch('alerts.views.messages')
    def test_acknowledge_missing_fingerprint(self, mock_messages):
        """Test acknowledgement fails with missing fingerprint."""
        request = self.factory.post(reverse('alerts:acknowledge-alert-from-list'), {
            'comment': 'Test comment',
            'next': '/alerts/'
        })
        request.user = self.user
        request = self.process_request_with_middleware(request)

        response = acknowledge_alert_from_list(request)

        mock_messages.error.assert_called_once_with(request, "Acknowledgement failed: Missing alert identifier.")
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response.url, reverse('alerts:alert-list')) # Should redirect to list view

    @patch('alerts.views.messages')
    def test_acknowledge_missing_comment(self, mock_messages):
        """Test acknowledgement fails with missing comment."""
        request = self.factory.post(reverse('alerts:acknowledge-alert-from-list') + '?page=2', {
            'fingerprint': 'test_fingerprint',
            'next': '/alerts/?page=2' # Simulate next URL with query params
        })
        request.user = self.user
        request = self.process_request_with_middleware(request)
        # request.GET is now a QueryDict because the query params were in the URL

        response = acknowledge_alert_from_list(request)

        mock_messages.error.assert_called_once_with(request, "Acknowledgement failed: Comment is required.")
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response.url, f"{reverse('alerts:alert-list')}?page=2") # Should redirect preserving query params

    @patch('alerts.views.get_object_or_404')
    @patch('alerts.views.acknowledge_alert')
    @patch('alerts.views.messages')
    def test_acknowledge_already_acknowledged(self, mock_messages, mock_acknowledge_alert, mock_get_object_or_404):
        """Test acknowledging an already acknowledged alert."""
        self.alert_group.acknowledged = True # Set as already acknowledged
        mock_get_object_or_404.return_value = self.alert_group

        request = self.factory.post(reverse('alerts:acknowledge-alert-from-list'), {
            'fingerprint': 'test_fingerprint',
            'comment': 'Another comment',
            'next': '/alerts/'
        })
        request.user = self.user
        request = self.process_request_with_middleware(request)

        response = acknowledge_alert_from_list(request)

        mock_get_object_or_404.assert_called_once_with(AlertGroup, fingerprint='test_fingerprint')
        mock_acknowledge_alert.assert_not_called() # Service function should not be called
        mock_messages.warning.assert_called_once_with(request, "Alert 'Test Alert' is already acknowledged.")
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response.url, '/alerts/') # Should redirect to next URL

    @patch('alerts.views.get_object_or_404')
    @patch('alerts.views.acknowledge_alert')
    @patch('alerts.views.messages')
    def test_acknowledge_service_exception(self, mock_messages, mock_acknowledge_alert, mock_get_object_or_404):
        """Test acknowledgement when the service function raises an exception."""
        mock_get_object_or_404.return_value = self.alert_group
        mock_acknowledge_alert.side_effect = Exception("Mock service error")

        request = self.factory.post(reverse('alerts:acknowledge-alert-from-list'), {
            'fingerprint': 'test_fingerprint',
            'comment': 'Test comment',
            'next': '/alerts/'
        })
        request.user = self.user
        request = self.process_request_with_middleware(request)

        response = acknowledge_alert_from_list(request)

        mock_get_object_or_404.assert_called_once_with(AlertGroup, fingerprint='test_fingerprint')
        mock_acknowledge_alert.assert_called_once_with(self.alert_group, self.user, 'Test comment')
        mock_messages.error.assert_called_once_with(request, "An error occurred while acknowledging the alert.")
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response.url, '/alerts/') # Should still redirect to next URL

    @patch('alerts.views.get_object_or_404')
    @patch('alerts.views.acknowledge_alert')
    @patch('alerts.views.messages')
    def test_acknowledge_success_no_next_url(self, mock_messages, mock_acknowledge_alert, mock_get_object_or_404):
        """Test successful acknowledgement when no 'next' URL is provided."""
        mock_get_object_or_404.return_value = self.alert_group

        request = self.factory.post(reverse('alerts:acknowledge-alert-from-list'), {
            'fingerprint': 'test_fingerprint',
            'comment': 'Test comment',
        }) # No 'next' parameter
        request.user = self.user
        request = self.process_request_with_middleware(request)

        response = acknowledge_alert_from_list(request)

        mock_get_object_or_404.assert_called_once_with(AlertGroup, fingerprint='test_fingerprint')
        mock_acknowledge_alert.assert_called_once_with(self.alert_group, self.user, 'Test comment')
        mock_messages.success.assert_called_once_with(request, "Alert 'Test Alert' acknowledged successfully.")
        self.assertIsInstance(response, HttpResponseRedirect)
        # Should redirect to the default alert list view
        self.assertEqual(response.url, reverse('alerts:alert-list'))