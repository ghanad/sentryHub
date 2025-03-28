from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.utils import timezone
from unittest.mock import patch

from ..models import AlertGroup, AlertInstance, AlertAcknowledgementHistory
from ..services.alerts_processor import acknowledge_alert


class AcknowledgeAlertTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.alert_group = AlertGroup.objects.create(
            name='Test Alert',
            fingerprint='test-fingerprint',
            current_status='firing',
            labels={'alertname': 'TestAlert'},
            severity='warning'
        )

    def tearDown(self):
        AlertAcknowledgementHistory.objects.all().delete()
        AlertInstance.objects.all().delete()
        AlertGroup.objects.all().delete()
        User.objects.all().delete()

    def test_acknowledge_alert_with_comment(self):
        """Test acknowledging an alert with a comment"""
        comment = "This is a test acknowledgement"
        
        result = acknowledge_alert(self.alert_group, self.user, comment)
        
        # Verify AlertGroup was updated
        self.alert_group.refresh_from_db()
        self.assertTrue(self.alert_group.acknowledged)
        self.assertEqual(self.alert_group.acknowledged_by, self.user)
        self.assertIsNotNone(self.alert_group.acknowledgement_time)
        
        # Verify AlertAcknowledgementHistory was created
        history = AlertAcknowledgementHistory.objects.first()
        self.assertEqual(history.alert_group, self.alert_group)
        self.assertEqual(history.acknowledged_by, self.user)
        self.assertEqual(history.comment, comment)
        self.assertIsNone(history.alert_instance)  # No active instance in this test

    def test_acknowledge_alert_without_comment(self):
        """Test acknowledging an alert without a comment"""
        result = acknowledge_alert(self.alert_group, self.user)
        
        # Verify AlertGroup was updated
        self.alert_group.refresh_from_db()
        self.assertTrue(self.alert_group.acknowledged)
        
        # Verify AlertAcknowledgementHistory was created with null comment
        history = AlertAcknowledgementHistory.objects.first()
        self.assertIsNone(history.comment)

    def test_acknowledge_alert_with_active_instance(self):
        """Test acknowledging an alert with an active firing instance"""
        active_instance = AlertInstance.objects.create(
            alert_group=self.alert_group,
            status='firing',
            started_at=timezone.now(),
            annotations={'summary': 'Test alert', 'description': 'Test description'},
            resolution_type=None
        )
        
        result = acknowledge_alert(self.alert_group, self.user)
        
        # Verify AlertAcknowledgementHistory was linked to the active instance
        history = AlertAcknowledgementHistory.objects.first()
        self.assertEqual(history.alert_instance, active_instance)
        self.assertEqual(history.alert_group, self.alert_group)
        self.assertEqual(history.acknowledged_by, self.user)

    @patch('alerts.services.alerts_processor.logger')
    def test_acknowledgement_logging(self, mock_logger):
        """Test that acknowledgement is properly logged"""
        acknowledge_alert(self.alert_group, self.user, "Test comment")
        
        # Verify logging calls
        self.assertTrue(mock_logger.info.called)
        calls = mock_logger.info.call_args_list
        self.assertIn("Alert acknowledged:", str(calls[0]))
        self.assertIn("Test Alert", str(calls[0]))
        self.assertIn("testuser", str(calls[0]))
