import json
import logging
from django.test import TestCase
from unittest.mock import patch, MagicMock
from alerts.tasks import process_alert_payload_task
from alerts.models import AlertGroup, AlertInstance

class ProcessAlertPayloadTaskTests(TestCase):
    def setUp(self):
        self.mock_payload = {
            "alerts": [
                {
                    "labels": {"alertname": "TestAlert", "env": "prod"},
                    "fingerprint": "test_fingerprint_1",
                    "status": "firing"
                }
            ]
        }
        self.mock_alert_group = MagicMock(spec=AlertGroup)
        self.mock_alert_group.id = 1
        self.mock_alert_group.name = "Test Alert Group"
        self.mock_alert_group.fingerprint = "test_fingerprint_1"
        self.mock_alert_group.current_status = "firing"

        self.mock_alert_instance = MagicMock(spec=AlertInstance)
        self.mock_alert_instance.id = 101

        # Capture logs for assertion
        self.logger = logging.getLogger('alerts.tasks')
        self.log_stream = MagicMock()
        self.logger.addHandler(logging.StreamHandler(self.log_stream))
        self.logger.setLevel(logging.INFO)

    @patch('alerts.tasks.parse_alertmanager_payload')
    @patch('alerts.tasks.update_alert_state')
    @patch('alerts.tasks.alert_processed.send')
    def test_process_alert_payload_task_success(self, mock_signal_send, mock_update_alert_state, mock_parse_payload):
        """
        Test successful processing of an alert payload.
        """
        mock_parse_payload.return_value = [self.mock_payload['alerts'][0]]
        mock_update_alert_state.return_value = (self.mock_alert_group, self.mock_alert_instance)

        result = process_alert_payload_task(json.dumps(self.mock_payload))

        mock_parse_payload.assert_called_once_with(self.mock_payload)
        mock_update_alert_state.assert_called_once_with(self.mock_payload['alerts'][0])
        mock_signal_send.assert_called_once_with(
            sender=self.mock_alert_group.__class__,
            alert_group=self.mock_alert_group,
            instance=self.mock_alert_instance,
            status=self.mock_alert_group.current_status
        )
        self.assertEqual(result, "Processed alerts successfully (Direct Call)")
        # Check if the log message exists in any of the calls
        log_messages = [call.args[0] for call in self.log_stream.write.call_args_list]
        self.assertTrue(any("Successfully processed alert. AlertGroup ID: 1, AlertInstance ID: 101" in msg for msg in log_messages))

    def test_process_alert_payload_task_invalid_json(self):
        """
        Test handling of invalid JSON payload.
        """
        invalid_json = "{'alerts': [" # Malformed JSON
        invalid_json = '{"alerts": [' # Corrected to use double quotes for keys

        result = process_alert_payload_task(invalid_json)

        self.assertIsNone(result) # Should return None on JSONDecodeError
        log_messages = [call.args[0] for call in self.log_stream.write.call_args_list]
        self.assertTrue(any("Failed to deserialize payload JSON:" in msg for msg in log_messages))

    @patch('alerts.tasks.parse_alertmanager_payload')
    @patch('alerts.tasks.update_alert_state')
    @patch('alerts.tasks.alert_processed.send')
    def test_process_alert_payload_task_empty_alerts(self, mock_signal_send, mock_update_alert_state, mock_parse_payload):
        """
        Test handling when payload parses into zero alerts.
        """
        mock_parse_payload.return_value = [] # Simulate no alerts parsed

        result = process_alert_payload_task(json.dumps(self.mock_payload))

        mock_parse_payload.assert_called_once_with(self.mock_payload)
        mock_update_alert_state.assert_not_called()
        mock_signal_send.assert_not_called()
        self.assertEqual(result, "Parsed zero alerts")
        self.assertIn("Payload parsed into zero alerts. No further processing.", self.log_stream.write.call_args[0][0])

    @patch('alerts.tasks.parse_alertmanager_payload', side_effect=Exception("Parsing Error"))
    def test_process_alert_payload_task_parsing_exception(self, mock_parse_payload):
        """
        Test handling of exceptions during payload parsing.
        """
        with self.assertRaisesRegex(Exception, "Parsing Error"):
            process_alert_payload_task(json.dumps(self.mock_payload))

        mock_parse_payload.assert_called_once_with(self.mock_payload)
        self.assertIn("Task failed during direct call: Parsing Error", self.log_stream.write.call_args[0][0])

    @patch('alerts.tasks.parse_alertmanager_payload')
    @patch('alerts.tasks.update_alert_state', side_effect=Exception("Update Error"))
    def test_process_alert_payload_task_update_exception(self, mock_update_alert_state, mock_parse_payload):
        """
        Test handling of exceptions during alert state update.
        """
        mock_parse_payload.return_value = [self.mock_payload['alerts'][0]]

        with self.assertRaisesRegex(Exception, "Update Error"):
            process_alert_payload_task(json.dumps(self.mock_payload))

        mock_parse_payload.assert_called_once_with(self.mock_payload)
        mock_update_alert_state.assert_called_once_with(self.mock_payload['alerts'][0])
        self.assertIn("Task failed during direct call: Update Error", self.log_stream.write.call_args[0][0])

    @patch('alerts.tasks.parse_alertmanager_payload')
    @patch('alerts.tasks.update_alert_state')
    @patch('alerts.tasks.alert_processed.send')
    def test_process_alert_payload_task_update_returns_none(self, mock_signal_send, mock_update_alert_state, mock_parse_payload):
        """
        Test handling when update_alert_state returns None (e.g., no changes made).
        """
        mock_parse_payload.return_value = [self.mock_payload['alerts'][0]]
        mock_update_alert_state.return_value = (None, None) # Simulate no group/instance returned

        result = process_alert_payload_task(json.dumps(self.mock_payload))

        mock_parse_payload.assert_called_once_with(self.mock_payload)
        mock_update_alert_state.assert_called_once_with(self.mock_payload['alerts'][0])
        mock_signal_send.assert_not_called()
        self.assertEqual(result, "Processed alerts successfully (Direct Call)")
        self.assertIn("update_alert_state returned None for alert:", self.log_stream.write.call_args[0][0])