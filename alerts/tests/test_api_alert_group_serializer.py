import datetime
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User
from alerts.models import AlertGroup, AlertInstance, AlertAcknowledgementHistory
from alerts.api.serializers import AlertGroupSerializer, AlertInstanceSerializer, AlertAcknowledgementHistorySerializer

class AlertGroupSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.alert_group_data = {
            'fingerprint': 'test_fingerprint_123',
            'name': 'Test Alert Group',
            'labels': {'severity': 'critical', 'env': 'production'},
            'severity': 'critical',
            'instance': 'server-1',
            'source': 'alertmanager-prod',
            'first_occurrence': timezone.now() - datetime.timedelta(hours=2),
            'last_occurrence': timezone.now(),
            'current_status': 'firing',
            'total_firing_count': 5,
            'acknowledged': False,
            'acknowledged_by': None,
            'acknowledgement_time': None,
            'is_silenced': False,
            'silenced_until': None,
            'jira_issue_key': None,
        }
        self.alert_group = AlertGroup.objects.create(**self.alert_group_data)

        self.alert_instance_data = {
            'alert_group': self.alert_group,
            'status': 'firing',
            'started_at': timezone.now() - datetime.timedelta(hours=1),
            'ended_at': None,
            'annotations': {'summary': 'Test instance firing'},
            'generator_url': 'http://example.com/generator',
        }
        self.alert_instance = AlertInstance.objects.create(**self.alert_instance_data)

        self.acknowledgement_history_data = {
            'alert_group': self.alert_group,
            'alert_instance': self.alert_instance,
            'acknowledged_by': self.user,
            'acknowledged_at': timezone.now(),
            'comment': 'Acknowledged for testing',
        }
        self.acknowledgement_history = AlertAcknowledgementHistory.objects.create(**self.acknowledgement_history_data)

    def test_alert_group_serializer_basic_fields(self):
        serializer = AlertGroupSerializer(instance=self.alert_group)
        data = serializer.data

        self.assertEqual(data['id'], self.alert_group.id)
        self.assertEqual(data['fingerprint'], self.alert_group.fingerprint)
        self.assertEqual(data['name'], self.alert_group.name)
        self.assertEqual(data['labels'], self.alert_group.labels)
        self.assertEqual(data['severity'], self.alert_group.severity)
        self.assertEqual(data['instance'], self.alert_group.instance)
        self.assertEqual(data['source'], self.alert_group.source)
        self.assertEqual(data['current_status'], self.alert_group.current_status)
        self.assertEqual(data['total_firing_count'], self.alert_group.total_firing_count)
        self.assertEqual(data['acknowledged'], self.alert_group.acknowledged)
        self.assertIsNone(data['acknowledged_by']) # Should be None as per setup
        self.assertIsNone(data['acknowledged_by_name']) # Should be None as per setup
        self.assertIsNone(data['acknowledgement_time']) # Should be None as per setup

        # Check datetime fields are serialized to ISO format with 'Z' for UTC
        self.assertTrue(data['first_occurrence'].endswith('Z'))
        self.assertTrue(data['last_occurrence'].endswith('Z'))

    def test_alert_group_serializer_acknowledged_by_name(self):
        self.alert_group.acknowledged_by = self.user
        self.alert_group.acknowledged = True
        self.alert_group.acknowledgement_time = timezone.now()
        self.alert_group.save()

        serializer = AlertGroupSerializer(instance=self.alert_group)
        data = serializer.data

        self.assertEqual(data['acknowledged_by_name'], self.user.get_full_name() or self.user.username)
        self.assertEqual(data['acknowledged_by'], self.user.id)
        self.assertIsNotNone(data['acknowledgement_time'])
        self.assertTrue(data['acknowledgement_time'].endswith('Z'))

    def test_alert_group_serializer_instances_nested(self):
        serializer = AlertGroupSerializer(instance=self.alert_group)
        data = serializer.data

        self.assertIn('instances', data)
        self.assertEqual(len(data['instances']), 1)
        
        instance_data = data['instances'][0]
        self.assertEqual(instance_data['id'], self.alert_instance.id)
        self.assertEqual(instance_data['status'], self.alert_instance.status)
        self.assertEqual(instance_data['alert_group_fingerprint'], self.alert_group.fingerprint)
        self.assertTrue(instance_data['started_at'].endswith('Z'))
        self.assertIsNone(instance_data['ended_at']) # As per setup

    def test_alert_group_serializer_acknowledgement_history_nested(self):
        serializer = AlertGroupSerializer(instance=self.alert_group)
        data = serializer.data

        self.assertIn('acknowledgement_history', data)
        self.assertEqual(len(data['acknowledgement_history']), 1)

        history_data = data['acknowledgement_history'][0]
        self.assertEqual(history_data['id'], self.acknowledgement_history.id)
        self.assertEqual(history_data['acknowledged_by'], self.user.id)
        self.assertEqual(history_data['acknowledged_by_name'], self.user.get_full_name() or self.user.username)
        self.assertEqual(history_data['comment'], self.acknowledgement_history.comment)
        self.assertTrue(history_data['acknowledged_at'].endswith('Z'))
        
        instance_details = history_data['instance_details']
        self.assertEqual(instance_details['id'], self.alert_instance.id)
        self.assertEqual(instance_details['status'], self.alert_instance.status)
        self.assertTrue(instance_details['started_at'].endswith('Z'))
        self.assertIsNone(instance_details['ended_at'])

    def test_alert_group_serializer_null_fields(self):
        alert_group_null_data = {
            'fingerprint': 'null_test_fingerprint',
            'name': 'Null Fields Alert Group',
            'labels': {},
            'severity': 'info',
            'instance': None,
            'source': None,
            'first_occurrence': timezone.now(),
            'last_occurrence': timezone.now(),
            'current_status': 'resolved',
            'total_firing_count': 1,
            'acknowledged': False,
            'acknowledged_by': None,
            'acknowledgement_time': None,
            'documentation': None,
            'is_silenced': False,
            'silenced_until': None,
            'jira_issue_key': None,
        }
        alert_group_with_nulls = AlertGroup.objects.create(**alert_group_null_data)
        serializer = AlertGroupSerializer(instance=alert_group_with_nulls)
        data = serializer.data

        self.assertIsNone(data['instance'])
        self.assertIsNone(data['source'])
        self.assertIsNone(data['acknowledged_by'])
        self.assertIsNone(data['acknowledged_by_name'])
        self.assertIsNone(data['acknowledgement_time'])
        self.assertIsNone(data['jira_issue_key'])
        self.assertIsNone(data['silenced_until'])
        self.assertEqual(len(data['instances']), 0)
        self.assertEqual(len(data['acknowledgement_history']), 0)