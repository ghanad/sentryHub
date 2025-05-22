from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from alerts.models import AlertGroup, AlertInstance, AlertAcknowledgementHistory
from alerts.api.serializers import AlertAcknowledgementHistorySerializer
from datetime import timedelta

class AlertAcknowledgementHistorySerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword', first_name='Test', last_name='User')
        self.alert_group = AlertGroup.objects.create(
            fingerprint='testfingerprint123',
            name='Test Alert',
            labels={'severity': 'critical'},
            current_status='firing'
        )
        self.alert_instance = AlertInstance.objects.create(
            alert_group=self.alert_group,
            status='firing',
            started_at=timezone.now().astimezone(timezone.utc) - timedelta(hours=1),
            ended_at=timezone.now().astimezone(timezone.utc), # Ensure ended_at is set for testing
            annotations={'summary': 'Test alert instance'}
        )
        self.acknowledgement_history = AlertAcknowledgementHistory.objects.create(
            alert_group=self.alert_group,
            alert_instance=self.alert_instance,
            acknowledged_by=self.user,
            comment='Acknowledged for testing',
            acknowledged_at=timezone.now().astimezone(timezone.utc) # Ensure acknowledged_at is timezone-aware
        )

    def test_serializer_contains_expected_fields(self):
        serializer = AlertAcknowledgementHistorySerializer(instance=self.acknowledgement_history)
        data = serializer.data
        self.assertCountEqual(data.keys(), ['id', 'acknowledged_by', 'acknowledged_by_name', 'acknowledged_at', 'comment', 'alert_instance', 'instance_details'])

    def test_acknowledged_by_name_field(self):
        serializer = AlertAcknowledgementHistorySerializer(instance=self.acknowledgement_history)
        self.assertEqual(serializer.data['acknowledged_by_name'], 'Test User')

        # Test with user having only username
        user_no_full_name = User.objects.create_user(username='onlyusername', password='testpassword')
        ack_no_full_name = AlertAcknowledgementHistory.objects.create(
            alert_group=self.alert_group,
            alert_instance=self.alert_instance,
            acknowledged_by=user_no_full_name,
            comment='Acknowledged by user with no full name'
        )
        serializer_no_full_name = AlertAcknowledgementHistorySerializer(instance=ack_no_full_name)
        self.assertEqual(serializer_no_full_name.data['acknowledged_by_name'], 'onlyusername')

        # Test with no acknowledged_by user
        ack_no_user = AlertAcknowledgementHistory.objects.create(
            alert_group=self.alert_group,
            alert_instance=self.alert_instance,
            acknowledged_by=None,
            comment='Acknowledged by no user'
        )
        serializer_no_user = AlertAcknowledgementHistorySerializer(instance=ack_no_user)
        self.assertIsNone(serializer_no_user.data['acknowledged_by_name'])

    def test_instance_details_field(self):
        serializer = AlertAcknowledgementHistorySerializer(instance=self.acknowledgement_history)
        instance_details = serializer.data['instance_details']
        self.assertIsNotNone(instance_details)
        self.assertEqual(instance_details['id'], self.alert_instance.id)
        
        expected_started_at_str = self.alert_instance.started_at.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
        self.assertEqual(instance_details['started_at'], expected_started_at_str)
        
        if self.alert_instance.ended_at:
            expected_ended_at_str = self.alert_instance.ended_at.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
            self.assertEqual(instance_details['ended_at'], expected_ended_at_str)
        else:
            self.assertIsNone(instance_details['ended_at'])

        self.assertEqual(instance_details['status'], self.alert_instance.status)

        # Test with no alert_instance
        ack_no_instance = AlertAcknowledgementHistory.objects.create(
            alert_group=self.alert_group,
            alert_instance=None,
            acknowledged_by=self.user,
            comment='Acknowledged with no instance'
        )
        serializer_no_instance = AlertAcknowledgementHistorySerializer(instance=ack_no_instance)
        self.assertIsNone(serializer_no_instance.data['instance_details'])

    def test_serialization_of_all_fields(self):
        serializer = AlertAcknowledgementHistorySerializer(instance=self.acknowledgement_history)
        data = serializer.data
        self.assertEqual(data['id'], self.acknowledgement_history.id)
        self.assertEqual(data['acknowledged_by'], self.user.id)
        
        expected_acknowledged_at_str = self.acknowledgement_history.acknowledged_at.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
        self.assertEqual(data['acknowledged_at'], expected_acknowledged_at_str)
        
        
        self.assertEqual(data['comment'], 'Acknowledged for testing')
        self.assertEqual(data['alert_instance'], self.alert_instance.id)