import json
import logging
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone

from alerts.models import AlertGroup, AlertInstance
# The task to be tested
from alerts.tasks import process_alert_payload_task

# Suppress logging output during tests unless specifically testing for it
logging.disable(logging.CRITICAL)

class ProcessAlertPayloadTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tasktestuser', password='password123')
        
        # Sample valid Alertmanager payload structure (can be customized per test)
        self.sample_alert_data1 = {
            'labels': {'alertname': 'TestAlert1', 'severity': 'critical', 'instance': 'serverA'},
            'annotations': {'summary': 'Summary for TestAlert1', 'description': 'Description for TestAlert1'},
            'startsAt': timezone.now().isoformat(),
            'status': 'firing', # This is part of the individual alert in Alertmanager v4
            'generatorURL': 'http://prometheus/g0',
            'fingerprint': 'fp1_task_test'
        }
        self.sample_alert_data2 = {
            'labels': {'alertname': 'TestAlert2', 'severity': 'warning', 'instance': 'serverB'},
            'annotations': {'summary': 'Summary for TestAlert2'},
            'startsAt': timezone.now().isoformat(),
            'status': 'firing',
            'generatorURL': 'http://prometheus/g1',
            'fingerprint': 'fp2_task_test'
        }

        self.alertmanager_payload_single = {
            "version": "4",
            "groupKey": "{}:{alertname=\"TestAlert1\"}",
            "status": "firing", # Common status for the group
            "receiver": "webhook-receiver",
            "groupLabels": {"alertname": "TestAlert1"},
            "commonLabels": {"alertname": "TestAlert1", "job": "testjob"},
            "commonAnnotations": {"common": "anno"},
            "externalURL": "http://alertmanager.example.com",
            "alerts": [self.sample_alert_data1]
        }

        self.alertmanager_payload_multiple = {
            "version": "4",
            "groupKey": "{}:{alertname=\"TestAlert1\"}", # Could be a more generic group key
            "status": "firing",
            "receiver": "webhook-receiver",
            "groupLabels": {},
            "commonLabels": {"job": "testjob"},
            "commonAnnotations": {},
            "externalURL": "http://alertmanager.example.com",
            "alerts": [self.sample_alert_data1, self.sample_alert_data2]
        }

        # Mock AlertGroup and AlertInstance to be returned by services
        self.mock_alert_group1 = AlertGroup(fingerprint='fp1_task_test', name='TestAlert1', severity='critical')
        self.mock_alert_instance1 = AlertInstance(alert_group=self.mock_alert_group1, status='firing')
        
        self.mock_alert_group2 = AlertGroup(fingerprint='fp2_task_test', name='TestAlert2', severity='warning')
        self.mock_alert_instance2 = AlertInstance(alert_group=self.mock_alert_group2, status='firing')

    @patch('alerts.tasks.alert_processed.send')
    @patch('alerts.tasks.update_alert_state')
    @patch('alerts.tasks.parse_alertmanager_payload')
    def test_process_valid_single_alert_payload(
        self, mock_parse_payload, mock_update_state, mock_alert_processed_send
    ):
        """ Test processing a valid payload with a single alert. """
        # Configure mocks
        mock_parse_payload.return_value = [self.sample_alert_data1] # Parser returns a list of alert dicts
        mock_update_state.return_value = (self.mock_alert_group1, self.mock_alert_instance1)

        payload_json = json.dumps(self.alertmanager_payload_single)
        process_alert_payload_task(None, payload_json) # Call the task function

        mock_parse_payload.assert_called_once_with(self.alertmanager_payload_single)
        mock_update_state.assert_called_once_with(self.sample_alert_data1)
        mock_alert_processed_send.assert_called_once_with(
            sender=process_alert_payload_task,
            alert_group=self.mock_alert_group1,
            instance=self.mock_alert_instance1,
            status=self.sample_alert_data1['status']
        )

    @patch('alerts.tasks.alert_processed.send')
    @patch('alerts.tasks.update_alert_state')
    @patch('alerts.tasks.parse_alertmanager_payload')
    def test_process_valid_multiple_alerts_payload(
        self, mock_parse_payload, mock_update_state, mock_alert_processed_send
    ):
        """ Test processing a valid payload with multiple alerts. """
        mock_parse_payload.return_value = [self.sample_alert_data1, self.sample_alert_data2]
        
        # Make update_alert_state return different values for different calls
        mock_update_state.side_effect = [
            (self.mock_alert_group1, self.mock_alert_instance1),
            (self.mock_alert_group2, self.mock_alert_instance2)
        ]

        payload_json = json.dumps(self.alertmanager_payload_multiple)
        process_alert_payload_task(None, payload_json)

        mock_parse_payload.assert_called_once_with(self.alertmanager_payload_multiple)
        
        # Check calls to update_alert_state
        self.assertEqual(mock_update_state.call_count, 2)
        mock_update_state.assert_any_call(self.sample_alert_data1)
        mock_update_state.assert_any_call(self.sample_alert_data2)

        # Check calls to alert_processed.send
        self.assertEqual(mock_alert_processed_send.call_count, 2)
        expected_signal_calls = [
            call(
                sender=process_alert_payload_task,
                alert_group=self.mock_alert_group1,
                instance=self.mock_alert_instance1,
                status=self.sample_alert_data1['status']
            ),
            call(
                sender=process_alert_payload_task,
                alert_group=self.mock_alert_group2,
                instance=self.mock_alert_instance2,
                status=self.sample_alert_data2['status']
            )
        ]
        mock_alert_processed_send.assert_has_calls(expected_signal_calls, any_order=False) # Order matters here due to side_effect

    @patch('alerts.tasks.alert_processed.send')
    @patch('alerts.tasks.update_alert_state')
    @patch('alerts.tasks.parse_alertmanager_payload')
    @patch('alerts.tasks.logger') # Mock the logger in tasks.py
    def test_process_empty_alerts_from_parser(
        self, mock_logger, mock_parse_payload, mock_update_state, mock_alert_processed_send
    ):
        """ Test processing when parser returns an empty list of alerts. """
        mock_parse_payload.return_value = [] # Parser returns no alerts

        payload_json = json.dumps(self.alertmanager_payload_single) # Payload content doesn't matter as parser is mocked
        process_alert_payload_task(None, payload_json)

        mock_parse_payload.assert_called_once_with(self.alertmanager_payload_single)
        mock_update_state.assert_not_called()
        mock_alert_processed_send.assert_not_called()
        
        # Check for specific log message
        mock_logger.info.assert_called_once()
        self.assertIn("Payload parsed into zero alerts.", mock_logger.info.call_args[0][0])

    @patch('alerts.tasks.alert_processed.send')
    @patch('alerts.tasks.update_alert_state')
    @patch('alerts.tasks.parse_alertmanager_payload')
    @patch('alerts.tasks.logger') # Mock the logger
    def test_process_update_alert_state_returns_none(
        self, mock_logger, mock_parse_payload, mock_update_state, mock_alert_processed_send
    ):
        """ Test processing when update_alert_state returns (None, None). """
        mock_parse_payload.return_value = [self.sample_alert_data1]
        mock_update_state.return_value = (None, None) # Simulate no group/instance returned

        payload_json = json.dumps(self.alertmanager_payload_single)
        process_alert_payload_task(None, payload_json)

        mock_parse_payload.assert_called_once_with(self.alertmanager_payload_single)
        mock_update_state.assert_called_once_with(self.sample_alert_data1)
        mock_alert_processed_send.assert_not_called()
        
        # Check for specific log message
        mock_logger.info.assert_called_once()
        self.assertIn(
            f"update_alert_state returned no alert_group or instance for alert data: {self.sample_alert_data1}",
            mock_logger.info.call_args[0][0]
        )

    @patch('alerts.tasks.alert_processed.send')
    @patch('alerts.tasks.update_alert_state')
    @patch('alerts.tasks.parse_alertmanager_payload')
    @patch('alerts.tasks.logger') # Mock the logger
    def test_process_invalid_json_payload(
        self, mock_logger, mock_parse_payload, mock_update_state, mock_alert_processed_send
    ):
        """ Test processing an invalid JSON payload string. """
        invalid_payload_json = "this is not valid json"
        
        process_alert_payload_task(None, invalid_payload_json)

        mock_parse_payload.assert_not_called()
        mock_update_state.assert_not_called()
        mock_alert_processed_send.assert_not_called()
        
        mock_logger.error.assert_called_once()
        # Check that the log message contains information about JSON decoding error
        self.assertIn("Failed to decode JSON payload", mock_logger.error.call_args[0][0])
        self.assertIn(invalid_payload_json, mock_logger.error.call_args[0][1]) # Original payload
        self.assertTrue(isinstance(mock_logger.error.call_args[0][2], json.JSONDecodeError)) # Exception instance

    @patch('alerts.tasks.alert_processed.send')
    @patch('alerts.tasks.update_alert_state')
    @patch('alerts.tasks.parse_alertmanager_payload')
    @patch('alerts.tasks.logger') # Mock the logger
    def test_process_general_exception_in_parse(
        self, mock_logger, mock_parse_payload, mock_update_state, mock_alert_processed_send
    ):
        """ Test general exception handling when parse_alertmanager_payload raises an error. """
        mock_parse_payload.side_effect = Exception("Parsing failed unexpectedly!")
        payload_json = json.dumps(self.alertmanager_payload_single)

        with self.assertRaises(Exception) as cm: # Check if the exception is re-raised
            process_alert_payload_task(None, payload_json)
        
        self.assertEqual(str(cm.exception), "Parsing failed unexpectedly!")

        mock_parse_payload.assert_called_once_with(self.alertmanager_payload_single)
        mock_update_state.assert_not_called()
        mock_alert_processed_send.assert_not_called()
        
        mock_logger.error.assert_called_once()
        self.assertIn("Error processing Alertmanager payload", mock_logger.error.call_args[0][0])
        self.assertTrue(isinstance(mock_logger.error.call_args[0][1], Exception))

    @patch('alerts.tasks.alert_processed.send')
    @patch('alerts.tasks.update_alert_state')
    @patch('alerts.tasks.parse_alertmanager_payload')
    @patch('alerts.tasks.logger') # Mock the logger
    def test_process_general_exception_in_update_state(
        self, mock_logger, mock_parse_payload, mock_update_state, mock_alert_processed_send
    ):
        """ Test general exception handling when update_alert_state raises an error. """
        mock_parse_payload.return_value = [self.sample_alert_data1]
        mock_update_state.side_effect = Exception("State update failed!")
        
        payload_json = json.dumps(self.alertmanager_payload_single)

        with self.assertRaises(Exception) as cm:
            process_alert_payload_task(None, payload_json)
            
        self.assertEqual(str(cm.exception), "State update failed!")

        mock_parse_payload.assert_called_once_with(self.alertmanager_payload_single)
        mock_update_state.assert_called_once_with(self.sample_alert_data1)
        mock_alert_processed_send.assert_not_called() # Should not be called if update_alert_state fails
        
        mock_logger.error.assert_called_once()
        self.assertIn("Error processing Alertmanager payload", mock_logger.error.call_args[0][0])
        self.assertTrue(isinstance(mock_logger.error.call_args[0][1], Exception))

    @patch('alerts.tasks.alert_processed.send')
    @patch('alerts.tasks.update_alert_state')
    @patch('alerts.tasks.parse_alertmanager_payload')
    @patch('alerts.tasks.logger') # Mock the logger
    def test_process_general_exception_in_signal_send(
        self, mock_logger, mock_parse_payload, mock_update_state, mock_alert_processed_send
    ):
        """ Test general exception handling when alert_processed.send raises an error. """
        mock_parse_payload.return_value = [self.sample_alert_data1]
        mock_update_state.return_value = (self.mock_alert_group1, self.mock_alert_instance1)
        mock_alert_processed_send.side_effect = Exception("Signal sending failed!")

        payload_json = json.dumps(self.alertmanager_payload_single)

        with self.assertRaises(Exception) as cm:
            process_alert_payload_task(None, payload_json)

        self.assertEqual(str(cm.exception), "Signal sending failed!")
        
        mock_parse_payload.assert_called_once_with(self.alertmanager_payload_single)
        mock_update_state.assert_called_once_with(self.sample_alert_data1)
        mock_alert_processed_send.assert_called_once_with(
            sender=process_alert_payload_task,
            alert_group=self.mock_alert_group1,
            instance=self.mock_alert_instance1,
            status=self.sample_alert_data1['status']
        )
        
        mock_logger.error.assert_called_once()
        self.assertIn("Error processing Alertmanager payload", mock_logger.error.call_args[0][0])
        self.assertTrue(isinstance(mock_logger.error.call_args[0][1], Exception))
