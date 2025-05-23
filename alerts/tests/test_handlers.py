from django.test import TestCase
from unittest.mock import patch, MagicMock
from alerts.models import AlertGroup
from alerts.signals import alert_processed
import logging

class AlertHandlersTests(TestCase):
    def setUp(self):
        self.alert_group = AlertGroup.objects.create(
            name='Test Alert',
            fingerprint='test_fingerprint',
            severity='critical',
            current_status='firing',
            labels={'alertname': 'TestAlert'}
        )
        # Capture logs for assertion
        self.logger = logging.getLogger('alerts.handlers')
        self.log_stream = MagicMock()
        self.logger.addHandler(logging.StreamHandler(self.log_stream))
        self.logger.setLevel(logging.INFO)

    @patch('alerts.handlers.check_alert_silence')
    def test_handle_silence_check_firing_silenced(self, mock_check_alert_silence):
        """
        Test handle_silence_check when alert is firing and becomes silenced.
        """
        mock_check_alert_silence.return_value = True # Simulate alert becoming silenced

        alert_processed.send(
            sender=self.__class__,
            alert_group=self.alert_group,
            instance=MagicMock(), # Mock AlertInstance
            status='firing'
        )

        mock_check_alert_silence.assert_called_once_with(self.alert_group)
        self.assertIn(
            f"Alerts Handler (Silence Check) (FP: {self.alert_group.fingerprint}): Alert {self.alert_group.name} (Group ID: {self.alert_group.id}) is firing but currently silenced.",
            self.log_stream.write.call_args[0][0]
        )

    @patch('alerts.handlers.check_alert_silence')
    def test_handle_silence_check_firing_not_silenced(self, mock_check_alert_silence):
        """
        Test handle_silence_check when alert is firing and remains not silenced.
        """
        mock_check_alert_silence.return_value = False # Simulate alert remaining not silenced
        self.alert_group.is_silenced = False # Ensure initial state is not silenced
        self.alert_group.save()

        alert_processed.send(
            sender=self.__class__,
            alert_group=self.alert_group,
            instance=MagicMock(),
            status='firing'
        )

        mock_check_alert_silence.assert_called_once_with(self.alert_group)
        # Assert no specific "silenced" or "no longer silenced" log message
        log_output = self.log_stream.write.call_args[0][0]
        self.assertNotIn("is firing but currently silenced", log_output)
        self.assertNotIn("was silenced but is no longer", log_output)

    @patch('alerts.handlers.check_alert_silence')
    def test_handle_silence_check_resolved_not_silenced(self, mock_check_alert_silence):
        """
        Test handle_silence_check when alert is resolved and remains not silenced.
        """
        mock_check_alert_silence.return_value = False # Simulate alert remaining not silenced
        self.alert_group.current_status = 'resolved'
        self.alert_group.is_silenced = False
        self.alert_group.save()

        alert_processed.send(
            sender=self.__class__,
            alert_group=self.alert_group,
            instance=MagicMock(),
            status='resolved'
        )

        mock_check_alert_silence.assert_called_once_with(self.alert_group)
        log_output = self.log_stream.write.call_args[0][0]
        self.assertNotIn("is firing but currently silenced", log_output)
        self.assertNotIn("was silenced but is no longer", log_output)

    @patch('alerts.handlers.check_alert_silence')
    def test_handle_silence_check_no_longer_silenced(self, mock_check_alert_silence):
        """
        Test handle_silence_check when alert was silenced but is no longer.
        """
        mock_check_alert_silence.return_value = False # Simulate alert no longer silenced
        self.alert_group.is_silenced = True # Set initial state to silenced
        self.alert_group.save()

        alert_processed.send(
            sender=self.__class__,
            alert_group=self.alert_group,
            instance=MagicMock(),
            status='firing' # Status doesn't matter as much as is_silenced state
        )

        mock_check_alert_silence.assert_called_once_with(self.alert_group)
        self.assertIn(
            f"Alerts Handler (Silence Check) (FP: {self.alert_group.fingerprint}): Alert {self.alert_group.name} (Group ID: {self.alert_group.id}) was silenced but is no longer.",
            self.log_stream.write.call_args[0][0]
        )

    @patch('alerts.handlers.check_alert_silence', side_effect=Exception("Test Error"))
    def test_handle_silence_check_exception_handling(self, mock_check_alert_silence):
        """
        Test that handle_silence_check gracefully handles exceptions during silence check.
        """
        alert_processed.send(
            sender=self.__class__,
            alert_group=self.alert_group,
            instance=MagicMock(),
            status='firing'
        )

        mock_check_alert_silence.assert_called_once_with(self.alert_group)
        self.assertIn(
            f"Alerts Handler (Silence Check) (FP: {self.alert_group.fingerprint}): Failed to check silence for alert {self.alert_group.id}: Test Error",
            self.log_stream.write.call_args[0][0]
        )

    @patch('alerts.handlers.check_alert_silence')
    def test_handle_silence_check_no_alert_group(self, mock_check_alert_silence):
        """
        Test handle_silence_check when alert_group is None.
        """
        alert_processed.send(
            sender=self.__class__,
            alert_group=None,
            instance=MagicMock(),
            status='firing'
        )
        mock_check_alert_silence.assert_not_called()
        self.assertIn(
            "Alerts Handler (Silence Check): Received alert_processed signal without alert_group.",
            self.log_stream.write.call_args[0][0]
        )