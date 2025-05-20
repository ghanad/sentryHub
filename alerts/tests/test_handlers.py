import logging
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock

from alerts.models import AlertGroup, AlertInstance
from alerts.signals import alert_processed
# The handler function to be tested
from alerts.handlers import handle_silence_check 

# Suppress logging output during tests unless specifically testing for it
logging.disable(logging.CRITICAL)

class HandleSilenceCheckSignalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='handler_test_user', password='password123')
        
        self.alert_group1 = AlertGroup.objects.create(
            fingerprint='handler-fp-ag1', 
            name='Handler Test AG1', 
            severity='critical',
            current_status='firing' # Initially firing
        )
        self.instance1_ag1 = AlertInstance.objects.create(
            alert_group=self.alert_group1,
            status='firing',
            started_at=timezone.now() - timedelta(hours=1),
            annotations={'summary': 'Instance for AG1'}
        )

        self.alert_group2 = AlertGroup.objects.create(
            fingerprint='handler-fp-ag2',
            name='Handler Test AG2',
            severity='warning',
            current_status='resolved' # Initially resolved
        )
        self.instance1_ag2 = AlertInstance.objects.create(
            alert_group=self.alert_group2,
            status='resolved',
            started_at=timezone.now() - timedelta(days=1),
            ended_at=timezone.now() - timedelta(hours=12),
            annotations={'summary': 'Instance for AG2 (resolved)'}
        )
        
        # A sender object for the signal, can be a mock or any class/object
        self.mock_sender = MagicMock()

    @patch('alerts.services.silence_matcher.check_alert_silence')
    def test_handle_silence_check_status_firing(self, mock_check_alert_silence):
        """ Test handle_silence_check when status is 'firing'. """
        alert_processed.send(
            sender=self.mock_sender,
            alert_group=self.alert_group1,
            instance=self.instance1_ag1,
            status='firing'
        )
        mock_check_alert_silence.assert_called_once_with(self.alert_group1)

    @patch('alerts.services.silence_matcher.check_alert_silence')
    def test_handle_silence_check_status_resolved(self, mock_check_alert_silence):
        """ Test handle_silence_check when status is 'resolved'. """
        # Even for resolved, the handler might re-evaluate silence status based on rules.
        alert_processed.send(
            sender=self.mock_sender,
            alert_group=self.alert_group2, # Initially resolved
            instance=self.instance1_ag2,
            status='resolved'
        )
        mock_check_alert_silence.assert_called_once_with(self.alert_group2)

    @patch('alerts.services.silence_matcher.check_alert_silence')
    @patch('alerts.handlers.logger') # Mock the logger used in handlers.py
    def test_handle_silence_check_alert_group_none(self, mock_logger, mock_check_alert_silence):
        """ Test handle_silence_check when alert_group is None. """
        alert_processed.send(
            sender=self.mock_sender,
            alert_group=None,
            instance=self.instance1_ag1, # Instance might still be present
            status='firing'
        )
        mock_check_alert_silence.assert_not_called()
        mock_logger.warning.assert_called_once_with(
            "handle_silence_check signal received with no alert_group for instance %s, status %s.",
            self.instance1_ag1.id if self.instance1_ag1 else None,
            'firing'
        )

    @patch('alerts.services.silence_matcher.check_alert_silence', side_effect=Exception("Service unavailable"))
    @patch('alerts.handlers.logger') # Mock the logger
    def test_handle_silence_check_exception_in_check_alert_silence(self, mock_logger, mock_check_alert_silence):
        """ Test exception handling when check_alert_silence raises an error. """
        with self.assertLogs(logger='alerts.handlers', level='ERROR') as cm:
            # The signal connection is in apps.py, so it should be active.
            # We directly call the handler here for more direct testing of its logic,
            # though sending the signal would also work if the apps are fully loaded.
             handle_silence_check(
                sender=self.mock_sender,
                alert_group=self.alert_group1,
                instance=self.instance1_ag1,
                status='firing'
            )
        
        mock_check_alert_silence.assert_called_once_with(self.alert_group1)
        # Check that an error was logged
        self.assertIn(
            f"Error in handle_silence_check for alert_group {self.alert_group1.fingerprint}: Service unavailable",
            cm.output[0] # Check the first log message
        )
        # Also check using the mocked logger if preferred for more specific call checks
        mock_logger.error.assert_called_once()
        self.assertIn("Error in handle_silence_check for alert_group", mock_logger.error.call_args[0][0])
        self.assertIn(self.alert_group1.fingerprint, mock_logger.error.call_args[0][1])

    @patch('alerts.services.silence_matcher.check_alert_silence')
    @patch('alerts.handlers.logger')
    def test_handle_silence_check_no_instance_provided(self, mock_logger, mock_check_alert_silence):
        """ Test handle_silence_check when instance is None (should still proceed if alert_group is present). """
        alert_processed.send(
            sender=self.mock_sender,
            alert_group=self.alert_group1,
            instance=None, # No instance
            status='firing'
        )
        mock_check_alert_silence.assert_called_once_with(self.alert_group1)
        # No warning should be logged if alert_group is present
        mock_logger.warning.assert_not_called()
