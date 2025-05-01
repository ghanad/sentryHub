from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.utils import timezone
from unittest.mock import patch
from datetime import timedelta
from alerts.models import AlertGroup, AlertInstance
from alerts.services.alerts_processor import get_active_firing_instance

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



class GetActiveFiringInstanceTests(TestCase):

    def setUp(self):
        """
        Set up test data for get_active_firing_instance tests.
        """
        self.alert_group_1 = AlertGroup.objects.create(
            fingerprint="fg1", name="Test Alert 1", labels={}, severity="critical"
        )
        self.alert_group_2 = AlertGroup.objects.create(
            fingerprint="fg2", name="Test Alert 2", labels={}, severity="warning"
        )

        # Instance for alert_group_1 (firing and active)
        self.active_instance_1 = AlertInstance.objects.create(
            alert_group=self.alert_group_1,
            status='firing',
            started_at=timezone.now() - timedelta(minutes=5),
            ended_at=None,
            annotations={}
        )

        # Instance for alert_group_1 (resolved)
        self.resolved_instance_1 = AlertInstance.objects.create(
            alert_group=self.alert_group_1,
            status='resolved',
            started_at=timezone.now() - timedelta(minutes=10),
            ended_at=timezone.now() - timedelta(minutes=8),
            annotations={}
        )

        # Instance for alert_group_2 (resolved)
        self.resolved_instance_2 = AlertInstance.objects.create(
            alert_group=self.alert_group_2,
            status='resolved',
            started_at=timezone.now() - timedelta(minutes=15),
            ended_at=timezone.now() - timedelta(minutes=12),
            annotations={}
        )

    def test_get_active_firing_instance_with_active_instance(self):
        """
        Test that get_active_firing_instance returns the correct instance when one is active and firing.
        """
        active_instance = get_active_firing_instance(self.alert_group_1)
        self.assertEqual(active_instance, self.active_instance_1)

    def test_get_active_firing_instance_with_no_firing_instances(self):
        """
        Test that get_active_firing_instance returns None when no instances are firing.
        """
        active_instance = get_active_firing_instance(self.alert_group_2)
        self.assertIsNone(active_instance)

    def test_get_active_firing_instance_with_only_resolved_instances(self):
        """
        Test that get_active_firing_instance returns None when only resolved instances exist.
        """
        # Create a new alert group with only resolved instances
        alert_group_3 = AlertGroup.objects.create(
            fingerprint="fg3", name="Test Alert 3", labels={}, severity="info"
        )
        AlertInstance.objects.create(
            alert_group=alert_group_3,
            status='resolved',
            started_at=timezone.now() - timedelta(minutes=20),
            ended_at=timezone.now() - timedelta(minutes=18),
            annotations={}
        )
        active_instance = get_active_firing_instance(alert_group_3)
        self.assertIsNone(active_instance)

    def test_get_active_firing_instance_with_multiple_instances(self):
        """
        Test that get_active_firing_instance returns the correct active firing instance among multiple instances.
        """
        # Add another resolved instance to alert_group_1
        AlertInstance.objects.create(
            alert_group=self.alert_group_1,
            status='resolved',
            started_at=timezone.now() - timedelta(minutes=25),
            ended_at=timezone.now() - timedelta(minutes=22),
            annotations={}
        )
        active_instance = get_active_firing_instance(self.alert_group_1)
        self.assertEqual(active_instance, self.active_instance_1)

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from alerts.models import AlertGroup, AlertInstance
from alerts.services.alert_state_manager import update_alert_state # Import the function

class UpdateAlertStateNewFiringTests(TestCase):

    def test_new_firing_alert_creates_group_and_instance(self):
        """
        Test that a new firing alert creates a new AlertGroup and AlertInstance.
        """
        parsed_data = {
            'fingerprint': 'new-fg-1',
            'status': 'firing',
            'labels': {'alertname': 'NewAlert', 'severity': 'critical', 'instance': 'host1'},
            'starts_at': timezone.now() - timedelta(minutes=1),
            'ends_at': None,
            'annotations': {'summary': 'This is a new alert'},
            'generator_url': 'http://example.com/generator'
        }

        self.assertEqual(AlertGroup.objects.count(), 0)
        self.assertEqual(AlertInstance.objects.count(), 0)

        alert_group, alert_instance = update_alert_state(parsed_data)

        self.assertIsNotNone(alert_group)
        self.assertIsNotNone(alert_instance)

        self.assertEqual(AlertGroup.objects.count(), 1)
        self.assertEqual(AlertInstance.objects.count(), 1)

        created_group = AlertGroup.objects.get(fingerprint='new-fg-1')
        self.assertEqual(created_group.name, 'NewAlert')
        self.assertEqual(created_group.current_status, 'firing')
        self.assertEqual(created_group.total_firing_count, 1)
        self.assertEqual(created_group.instance, 'host1')
        self.assertFalse(created_group.acknowledged)
        self.assertIsNone(created_group.acknowledged_by)
        self.assertIsNone(created_group.acknowledgement_time)
        self.assertFalse(created_group.is_silenced)
        self.assertIsNone(created_group.silenced_until)
        self.assertIsNone(created_group.jira_issue_key)
        # Check labels and first/last occurrence are set (within a reasonable time frame)
        self.assertDictEqual(created_group.labels, {'alertname': 'NewAlert', 'severity': 'critical', 'instance': 'host1'})
        self.assertAlmostEqual(created_group.first_occurrence, timezone.now(), delta=timedelta(seconds=5))
        self.assertAlmostEqual(created_group.last_occurrence, timezone.now(), delta=timedelta(seconds=5))


        created_instance = AlertInstance.objects.get(alert_group=created_group)
        self.assertEqual(created_instance.status, 'firing')
        self.assertEqual(created_instance.started_at, parsed_data['starts_at'])
        self.assertIsNone(created_instance.ended_at)
        self.assertDictEqual(created_instance.annotations, parsed_data['annotations'])
        self.assertEqual(created_instance.generator_url, parsed_data['generator_url'])
        self.assertIsNone(created_instance.resolution_type)
        self.assertEqual(created_instance.alert_group, created_group)
def test_firing_alert_updates_existing_group_and_resolves_previous_instance(self):
        """
        Test that a firing alert for an existing group creates a new instance
        and resolves the previous firing instance.
        """
        # Create an initial alert group and a firing instance
        initial_starts_at = timezone.now() - timedelta(minutes=10)
        alert_group = AlertGroup.objects.create(
            fingerprint="existing-fg-1",
            name="Existing Alert",
            labels={'alertname': 'ExistingAlert'},
            severity="warning",
            current_status='firing',
            first_occurrence=initial_starts_at,
            last_occurrence=initial_starts_at,
            total_firing_count=1
        )
        initial_instance = AlertInstance.objects.create(
            alert_group=alert_group,
            status='firing',
            started_at=initial_starts_at,
            ended_at=None,
            annotations={'summary': 'Initial firing'},
            generator_url='http://example.com/initial'
        )

        self.assertEqual(AlertGroup.objects.count(), 1)
        self.assertEqual(AlertInstance.objects.count(), 1)

        # Receive a new firing alert for the same group
        new_starts_at = timezone.now() - timedelta(minutes=1)
        parsed_data = {
            'fingerprint': 'existing-fg-1',
            'status': 'firing',
            'labels': {'alertname': 'ExistingAlert', 'severity': 'warning'},
            'starts_at': new_starts_at,
            'ends_at': None,
            'annotations': {'summary': 'New firing event'},
            'generator_url': 'http://example.com/new'
        }

        updated_group, new_instance = update_alert_state(parsed_data)

        # Assertions for the AlertGroup
        self.assertEqual(AlertGroup.objects.count(), 1)
        updated_group.refresh_from_db() # Refresh to get latest state
        self.assertEqual(updated_group.current_status, 'firing')
        self.assertAlmostEqual(updated_group.last_occurrence, timezone.now(), delta=timedelta(seconds=5))
        self.assertEqual(updated_group.total_firing_count, 2) # Should increment

        # Assertions for the instances
        self.assertEqual(AlertInstance.objects.count(), 2)

        initial_instance.refresh_from_db() # Refresh to get latest state
        self.assertEqual(initial_instance.status, 'resolved')
        self.assertIsNone(initial_instance.ended_at) # Should be inferred resolution, ended_at is NULL
        self.assertEqual(initial_instance.resolution_type, 'inferred')

        self.assertIsNotNone(new_instance)
        self.assertEqual(new_instance.alert_group, updated_group)
        self.assertEqual(new_instance.status, 'firing')
        self.assertEqual(new_instance.started_at, new_starts_at)
        self.assertIsNone(new_instance.ended_at)
        self.assertDictEqual(new_instance.annotations, parsed_data['annotations'])
        self.assertEqual(new_instance.generator_url, parsed_data['generator_url'])
        self.assertIsNone(new_instance.resolution_type)
        
