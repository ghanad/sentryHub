from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, call

from alerts.models import AlertGroup, SilenceRule
# Functions to be tested or mocked will be imported within tests or via patch

class SilenceRuleSignalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='signaltestuser', password='password123')
        
        # Create some AlertGroups for the _rescan_alerts_for_silence tests
        self.ag_firing1 = AlertGroup.objects.create(
            fingerprint='signal-fp-firing1', 
            name='Signal Test Firing Alert 1', 
            severity='critical', 
            current_status='firing'
        )
        self.ag_firing2 = AlertGroup.objects.create(
            fingerprint='signal-fp-firing2', 
            name='Signal Test Firing Alert 2', 
            severity='warning', 
            current_status='firing'
        )
        self.ag_resolved1 = AlertGroup.objects.create(
            fingerprint='signal-fp-resolved1', 
            name='Signal Test Resolved Alert 1', 
            severity='info', 
            current_status='resolved'
        )
        
        self.silence_rule_data = {
            'matchers': {'job': 'test_signal_job'},
            'starts_at': timezone.now() - timedelta(hours=1),
            'ends_at': timezone.now() + timedelta(hours=1),
            'created_by': self.user,
            'comment': 'Test rule for signals'
        }

    @patch('alerts.signals._rescan_alerts_for_silence')
    def test_handle_silence_rule_save_created(self, mock_rescan_alerts):
        """ Test that _rescan_alerts_for_silence is called when a new SilenceRule is created. """
        # The signal is connected to SilenceRule.post_save
        # Creating a new rule will trigger the signal
        new_rule = SilenceRule.objects.create(**self.silence_rule_data)
        
        # Check if the mock was called
        mock_rescan_alerts.assert_called_once()
        # Check the first argument of the first call (the rule instance)
        # Note: The signal sends sender, instance, created, etc.
        # The receiver handle_silence_rule_save is expected to call _rescan_alerts_for_silence(instance)
        args, kwargs = mock_rescan_alerts.call_args
        self.assertEqual(args[0], new_rule) # The instance passed to _rescan_alerts_for_silence

    @patch('alerts.signals._rescan_alerts_for_silence')
    def test_handle_silence_rule_save_updated(self, mock_rescan_alerts):
        """ Test that _rescan_alerts_for_silence is called when an existing SilenceRule is updated. """
        # Create an initial rule
        rule_to_update = SilenceRule.objects.create(**self.silence_rule_data)
        mock_rescan_alerts.reset_mock() # Reset mock from the creation save

        # Update the rule
        rule_to_update.comment = "Updated comment for signal test"
        rule_to_update.save() # This triggers the post_save signal again

        mock_rescan_alerts.assert_called_once()
        args, kwargs = mock_rescan_alerts.call_args
        self.assertEqual(args[0], rule_to_update)

    @patch('alerts.signals._rescan_alerts_for_silence')
    def test_handle_silence_rule_delete(self, mock_rescan_alerts):
        """ Test that _rescan_alerts_for_silence is called when a SilenceRule is deleted. """
        # Create a rule
        rule_to_delete = SilenceRule.objects.create(**self.silence_rule_data)
        mock_rescan_alerts.reset_mock() # Reset from creation save if any

        # Delete the rule
        rule_to_delete.delete() # This triggers the post_delete signal

        mock_rescan_alerts.assert_called_once()
        args, kwargs = mock_rescan_alerts.call_args
        # The instance passed to the signal handler (and thus to _rescan_alerts_for_silence)
        # will be the instance that was just deleted.
        # We can't compare it directly by PK as it might be unsaved, but its attributes should match.
        self.assertEqual(args[0].fingerprint, rule_to_delete.fingerprint) # Check a unique attribute
        self.assertEqual(args[0].matchers, rule_to_delete.matchers)

# Import the function to be tested directly (if not already imported for mocking)
from alerts.signals import _rescan_alerts_for_silence

class RescanAlertsForSilenceFunctionTests(TestCase): # New test class for the function itself
    def setUp(self):
        self.user = User.objects.create_user(username='rescanuser', password='password123')
        
        self.ag_firing1 = AlertGroup.objects.create(
            fingerprint='rescan-fp-firing1', name='Rescan Test Firing 1', 
            severity='critical', current_status='firing'
        )
        self.ag_firing2 = AlertGroup.objects.create(
            fingerprint='rescan-fp-firing2', name='Rescan Test Firing 2', 
            severity='warning', current_status='firing'
        )
        self.ag_resolved1 = AlertGroup.objects.create(
            fingerprint='rescan-fp-resolved1', name='Rescan Test Resolved 1', 
            severity='info', current_status='resolved'
        )
        self.ag_firing_silenced_initially = AlertGroup.objects.create(
            fingerprint='rescan-fp-firing-silenced', name='Rescan Test Firing Silenced', 
            severity='critical', current_status='firing', is_silenced=True 
        )

        self.test_rule = SilenceRule.objects.create(
            matchers={'job': 'rescan_job'},
            starts_at=timezone.now() - timedelta(hours=1),
            ends_at=timezone.now() + timedelta(hours=1),
            created_by=self.user,
            comment='Rule for rescan test'
        )

    @patch('alerts.services.silence_matcher.check_alert_silence')
    def test_rescan_alerts_calls_check_alert_silence_for_non_resolved(self, mock_check_alert_silence):
        """
        Test that _rescan_alerts_for_silence calls check_alert_silence 
        for each non-resolved AlertGroup.
        """
        _rescan_alerts_for_silence(self.test_rule)

        # Expected calls: ag_firing1, ag_firing2, ag_firing_silenced_initially
        # Not called for ag_resolved1
        self.assertEqual(mock_check_alert_silence.call_count, 3)
        
        expected_calls = [
            call(self.ag_firing1),
            call(self.ag_firing2),
            call(self.ag_firing_silenced_initially)
        ]
        mock_check_alert_silence.assert_has_calls(expected_calls, any_order=True)

    @patch('alerts.services.silence_matcher.check_alert_silence')
    def test_rescan_alerts_no_non_resolved_alerts(self, mock_check_alert_silence):
        """
        Test _rescan_alerts_for_silence when there are no non-resolved alerts.
        """
        # Change all existing alerts to 'resolved'
        AlertGroup.objects.update(current_status='resolved')
        
        _rescan_alerts_for_silence(self.test_rule)
        
        mock_check_alert_silence.assert_not_called()

    @patch('alerts.services.silence_matcher.check_alert_silence')
    def test_rescan_alerts_no_alerts_at_all(self, mock_check_alert_silence):
        """
        Test _rescan_alerts_for_silence when there are no AlertGroup objects at all.
        """
        AlertGroup.objects.all().delete()
        
        _rescan_alerts_for_silence(self.test_rule)
        
        mock_check_alert_silence.assert_not_called()

    @patch('alerts.services.silence_matcher.check_alert_silence')
    def test_rescan_alerts_no_rule_passed(self, mock_check_alert_silence):
        """
        Test _rescan_alerts_for_silence when no rule (None) is passed.
        It should still iterate through non-resolved alerts.
        """
        _rescan_alerts_for_silence(None) # Pass None as the rule

        self.assertEqual(mock_check_alert_silence.call_count, 3)
        expected_calls = [
            call(self.ag_firing1),
            call(self.ag_firing2),
            call(self.ag_firing_silenced_initially)
        ]
        mock_check_alert_silence.assert_has_calls(expected_calls, any_order=True)
