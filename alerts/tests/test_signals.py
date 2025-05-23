from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch, MagicMock
from alerts.models import SilenceRule, AlertGroup
from django.contrib.auth import get_user_model
import datetime

User = get_user_model()

class SilenceRuleSignalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.alert_group_1 = AlertGroup.objects.create(
            name='Test Alert 1',
            fingerprint='fingerprint1',
            severity='critical',
            current_status='firing',
            labels={'alertname': 'TestAlert', 'env': 'prod'}
        )
        self.alert_group_2 = AlertGroup.objects.create(
            name='Test Alert 2',
            fingerprint='fingerprint2',
            severity='warning',
            current_status='firing',
            labels={'alertname': 'AnotherAlert', 'env': 'dev'}
        )
        self.alert_group_resolved = AlertGroup.objects.create(
            name='Resolved Alert',
            fingerprint='fingerprint_res',
            severity='info',
            current_status='resolved',
            labels={'alertname': 'ResolvedAlert', 'env': 'prod'}
        )

    @patch('alerts.signals._rescan_alerts_for_silence')
    def test_handle_silence_rule_save_on_create(self, mock_rescan):
        """
        Test that _rescan_alerts_for_silence is called when a SilenceRule is created.
        """
        SilenceRule.objects.create(
            matchers={'alertname': 'TestAlert'},
            starts_at=timezone.now(),
            ends_at=timezone.now() + datetime.timedelta(hours=1),
            comment='Test rule',
            created_by=self.user
        )
        mock_rescan.assert_called_once()

    @patch('alerts.signals._rescan_alerts_for_silence')
    def test_handle_silence_rule_save_on_update(self, mock_rescan):
        """
        Test that _rescan_alerts_for_silence is called when a SilenceRule is updated.
        """
        rule = SilenceRule.objects.create(
            matchers={'alertname': 'TestAlert'},
            starts_at=timezone.now(),
            ends_at=timezone.now() + datetime.timedelta(hours=1),
            comment='Test rule',
            created_by=self.user
        )
        mock_rescan.reset_mock() # Reset mock after creation call

        rule.comment = 'Updated comment'
        rule.save()
        mock_rescan.assert_called_once()

    @patch('alerts.signals._rescan_alerts_for_silence')
    def test_handle_silence_rule_delete(self, mock_rescan):
        """
        Test that _rescan_alerts_for_silence is called when a SilenceRule is deleted.
        """
        rule = SilenceRule.objects.create(
            matchers={'alertname': 'TestAlert'},
            starts_at=timezone.now(),
            ends_at=timezone.now() + datetime.timedelta(hours=1),
            comment='Test rule',
            created_by=self.user
        )
        mock_rescan.reset_mock() # Reset mock after creation call

        rule.delete()
        mock_rescan.assert_called_once()

    @patch('alerts.signals.check_alert_silence')
    def test_rescan_alerts_for_silence_logic(self, mock_check_alert_silence):
        """
        Test the internal logic of _rescan_alerts_for_silence, ensuring it queries
        non-resolved alerts and calls check_alert_silence for each.
        """
        from alerts.signals import _rescan_alerts_for_silence

        # Call the function directly
        _rescan_alerts_for_silence()

        # Assert that check_alert_silence was called for the two firing alerts
        self.assertEqual(mock_check_alert_silence.call_count, 2)
        
        # Verify calls with specific alert groups
        called_alert_groups = [call.args[0] for call in mock_check_alert_silence.call_args_list]
        self.assertIn(self.alert_group_1, called_alert_groups)
        self.assertIn(self.alert_group_2, called_alert_groups)
        self.assertNotIn(self.alert_group_resolved, called_alert_groups)