# alerts/tests/test_api_views.py

import json as actual_json_module # Standard library json
from unittest.mock import patch, MagicMock
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
import logging # For assertLogs

class AlertWebhookViewTests(APITestCase):
    def setUp(self):
        self.url = reverse('alerts:alert-webhook')
        self.valid_payload = {
            "version": "4",
            "groupKey": "{}:{alertname=\\\"test\\\"}",
            "truncatedAlerts": 0,
            "status": "firing",
            "receiver": "webhook",
            "groupLabels": {"alertname": "test"},
            "commonLabels": {"alertname": "test", "instance": "localhost:9090"},
            "commonAnnotations": {"summary": "Test alert"},
            "externalURL": "http://localhost:9093",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {"alertname": "test", "instance": "localhost:9090"},
                    "annotations": {"summary": "Test alert"},
                    "startsAt": "2023-01-01T00:00:00Z",
                    "endsAt": "0001-01-01T00:00:00Z"
                }
            ]
        }
        self.payload_with_bad_date_in_alert = {
            "version": "4",
            "receiver": "webhook",
            "status": "firing",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {"alertname": "test"},
                    "annotations": {"summary": "Test alert"},
                    "startsAt": "invalid-date-format",
                    "endsAt": "0001-01-01T00:00:00Z"
                }
            ]
        }

    @patch('alerts.api.views.process_alert_payload_task')
    def test_post_valid_payload(self, mock_process_alert_payload_task):
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'status': 'success (task queued)'})
        mock_process_alert_payload_task.delay.assert_called_once()
        args, _ = mock_process_alert_payload_task.delay.call_args
        self.assertIsInstance(args[0], str)
        self.assertDictEqual(actual_json_module.loads(args[0]), self.valid_payload)

    @patch('alerts.api.views.process_alert_payload_task')
    def test_post_invalid_payload_structure_missing_alerts_field(self, mock_process_alert_payload_task):
        payload_missing_alerts = {
            "version": "4",
            "status": "firing",
            "receiver": "webhook",
        }
        # Capture expected warning log from DRF/Django for bad request
        with self.assertLogs(logger='django.request', level='WARNING') as cm_django_warning:
            response = self.client.post(self.url, payload_missing_alerts, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('alerts', response.json())
        self.assertEqual(response.json()['alerts'][0], 'This field is required.')
        mock_process_alert_payload_task.delay.assert_not_called()
        self.assertTrue(any("Bad Request: /alerts/api/v1/webhook/" in log_line for log_line in cm_django_warning.output))


    @patch('alerts.api.views.process_alert_payload_task')
    def test_post_payload_with_bad_date_passes_initial_serialization(self, mock_process_alert_payload_task):
        response = self.client.post(self.url, self.payload_with_bad_date_in_alert, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'status': 'success (task queued)'})
        mock_process_alert_payload_task.delay.assert_called_once()

    @patch('alerts.api.views.AlertmanagerWebhookSerializer')
    @patch('alerts.api.views.json') # Patch the json module as seen by alerts.api.views
    @patch('alerts.api.views.process_alert_payload_task')
    def test_post_serialization_error(self, mock_process_alert_payload_task, mock_view_json_module, MockAlertmanagerWebhookSerializer):
        mock_serializer_instance = MockAlertmanagerWebhookSerializer.return_value
        mock_serializer_instance.is_valid.return_value = True
        mock_view_json_module.dumps.side_effect = TypeError("Mocked TypeError for view's json.dumps(request.data)")

        original_raise_setting = self.client.raise_request_exception
        self.client.raise_request_exception = False
        
        response = None
        try:
            # Catch the ERROR log made by the view ('alerts.api.views' logger)
            with self.assertLogs('alerts.api.views', level='ERROR') as cm_view_logger:
                # Also catch the generic 500 log from Django's request handler
                with self.assertLogs('django.request', level='ERROR') as cm_django_request_logger:
                    response = self.client.post(self.url, self.valid_payload, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
            self.assertEqual(response.json(), {'status': 'error serializing payload'})
            
            # Check if the specific log message from the view was emitted
            self.assertIn("Could not serialize payload to JSON: Mocked TypeError for view's json.dumps(request.data)", cm_view_logger.output[0])
            # Check if Django logged the 500
            self.assertTrue(any("Internal Server Error: /alerts/api/v1/webhook/" in log_line for log_line in cm_django_request_logger.output))
        finally:
            self.client.raise_request_exception = original_raise_setting
            
        mock_process_alert_payload_task.delay.assert_not_called()
        mock_view_json_module.dumps.assert_called_once_with(self.valid_payload)


    @patch('alerts.api.views.AlertmanagerWebhookSerializer')
    @patch('alerts.api.views.process_alert_payload_task')
    def test_post_celery_task_exception(self, mock_process_alert_payload_task, MockAlertmanagerWebhookSerializer):
        mock_serializer_instance = MockAlertmanagerWebhookSerializer.return_value
        mock_serializer_instance.is_valid.return_value = True
        mock_process_alert_payload_task.delay.side_effect = Exception("Celery task error")
        
        original_raise_setting = self.client.raise_request_exception
        self.client.raise_request_exception = False
        
        response = None
        try:
            # Catch the ERROR log made by Django's request handler for unhandled exceptions
            with self.assertLogs('django.request', level='ERROR') as cm_django_request_logger:
                response = self.client.post(self.url, self.valid_payload, format='json')

            self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
            # Check if the specific log message from django.request was emitted
            self.assertTrue(any("Internal Server Error: /alerts/api/v1/webhook/" in log_line for log_line in cm_django_request_logger.output))
            self.assertTrue(any("Celery task error" in log_line for log_line in cm_django_request_logger.output))
        finally:
            self.client.raise_request_exception = original_raise_setting
            
        mock_process_alert_payload_task.delay.assert_called_once()