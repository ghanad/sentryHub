import unittest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import serializers

# Import models and serializers from the alerts app
from alerts.models import AlertGroup, AlertInstance, AlertComment, AlertAcknowledgementHistory
from alerts.api.serializers import (
    AlertInstanceSerializer,
    AlertAcknowledgementHistorySerializer,
    AlertGroupSerializer,
    AlertCommentSerializer,
    AlertmanagerWebhookSerializer,
    AcknowledgeAlertSerializer
)


class AlertInstanceSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
        
        self.alert_group = AlertGroup.objects.create(
            fingerprint='test-fingerprint-123',
            name='Test Alert',
            labels={'severity': 'critical'},
            severity='critical',
            source='prometheus',
            first_occurrence=datetime.now(timezone.utc),
            last_occurrence=datetime.now(timezone.utc),
            current_status='firing'
        )
        
        self.alert_instance = AlertInstance.objects.create(
            alert_group=self.alert_group,
            status='firing',
            started_at=datetime.now(timezone.utc),
            annotations={'description': 'Test alert'},
            generator_url='http://prometheus:9090/graph'
        )

    def test_alert_instance_serializer_fields(self):
        serializer = AlertInstanceSerializer(instance=self.alert_instance)
        data = serializer.data
        
        expected_fields = [
            'id', 'status', 'started_at', 'ended_at', 
            'annotations', 'generator_url', 'alert_group_fingerprint'
        ]
        
        for field in expected_fields:
            self.assertIn(field, data)

    def test_get_alert_group_fingerprint_with_group(self):
        serializer = AlertInstanceSerializer(instance=self.alert_instance)
        fingerprint = serializer.get_alert_group_fingerprint(self.alert_instance)
        self.assertEqual(fingerprint, 'test-fingerprint-123')

    def test_get_alert_group_fingerprint_without_group(self):
        # Create instance without alert group
        instance_without_group = Mock()
        instance_without_group.alert_group = None
        
        serializer = AlertInstanceSerializer()
        fingerprint = serializer.get_alert_group_fingerprint(instance_without_group)
        self.assertIsNone(fingerprint)

    def test_datetime_formatting(self):
        serializer = AlertInstanceSerializer(instance=self.alert_instance)
        data = serializer.data
        
        # Check that datetime is formatted correctly
        self.assertRegex(data['started_at'], r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z')
        
        # ended_at should be None if not set
        self.assertIsNone(data['ended_at'])


class AlertAcknowledgementHistorySerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
        
        # Create mock acknowledgement for method testing
        self.mock_acknowledgement = Mock()
        self.mock_acknowledgement.id = 1
        self.mock_acknowledgement.acknowledged_by = self.user
        self.mock_acknowledgement.acknowledged_at = datetime.now(timezone.utc)
        self.mock_acknowledgement.comment = 'Acknowledged for testing'
        
        # Create mock alert instance
        self.mock_alert_instance = Mock()
        self.mock_alert_instance.id = 1
        self.mock_alert_instance.started_at = datetime.now(timezone.utc)
        self.mock_alert_instance.ended_at = None
        self.mock_alert_instance.status = 'firing'
        
        self.mock_acknowledgement.alert_instance = self.mock_alert_instance

    def test_acknowledgement_serializer_fields(self):
        # Test serializer fields with mock data
        serializer = AlertAcknowledgementHistorySerializer()
        expected_fields = [
            'id', 'acknowledged_by', 'acknowledged_by_name', 'acknowledged_at',
            'comment', 'alert_instance', 'instance_details'
        ]
        
        for field in expected_fields:
            self.assertIn(field, serializer.fields)

    def test_get_acknowledged_by_name_with_full_name(self):
        serializer = AlertAcknowledgementHistorySerializer()
        name = serializer.get_acknowledged_by_name(self.mock_acknowledgement)
        self.assertEqual(name, 'Test User')

    def test_get_acknowledged_by_name_without_full_name(self):
        user_no_name = User.objects.create_user(username='noname')
        acknowledgement = Mock()
        acknowledgement.acknowledged_by = user_no_name
        
        serializer = AlertAcknowledgementHistorySerializer()
        name = serializer.get_acknowledged_by_name(acknowledgement)
        self.assertEqual(name, 'noname')

    def test_get_acknowledged_by_name_no_user(self):
        acknowledgement = Mock()
        acknowledgement.acknowledged_by = None
        
        serializer = AlertAcknowledgementHistorySerializer()
        name = serializer.get_acknowledged_by_name(acknowledgement)
        self.assertIsNone(name)

    def test_get_instance_details_with_instance(self):
        serializer = AlertAcknowledgementHistorySerializer()
        details = serializer.get_instance_details(self.mock_acknowledgement)
        
        self.assertIsInstance(details, dict)
        self.assertIn('id', details)
        self.assertIn('started_at', details)
        self.assertIn('ended_at', details)
        self.assertIn('status', details)
        self.assertEqual(details['status'], 'firing')

    def test_get_instance_details_without_instance(self):
        acknowledgement = Mock()
        acknowledgement.alert_instance = None
        
        serializer = AlertAcknowledgementHistorySerializer()
        details = serializer.get_instance_details(acknowledgement)
        self.assertIsNone(details)


class AlertGroupSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
        
        self.alert_group = AlertGroup.objects.create(
            fingerprint='test-fingerprint-123',
            name='Test Alert',
            labels={'severity': 'critical'},
            severity='critical',
            source='prometheus',
            first_occurrence=datetime.now(timezone.utc),
            last_occurrence=datetime.now(timezone.utc),
            current_status='firing',
            acknowledged_by=self.user,
            acknowledgement_time=datetime.now(timezone.utc)
        )

    def test_alert_group_serializer_fields(self):
        serializer = AlertGroupSerializer(instance=self.alert_group)
        data = serializer.data
        
        expected_fields = [
            'id', 'fingerprint', 'name', 'labels', 'severity',
            'instance', 'source', 'first_occurrence', 'last_occurrence', 'current_status',
            'total_firing_count', 'acknowledged', 'acknowledged_by',
            'acknowledged_by_name', 'acknowledgement_time', 'instances',
            'acknowledgement_history', 'documentation', 'is_silenced', 'silenced_until', 'jira_issue_key'
        ]
        
        for field in expected_fields:
            self.assertIn(field, data)

    def test_get_acknowledged_by_name_with_user(self):
        serializer = AlertGroupSerializer()
        name = serializer.get_acknowledged_by_name(self.alert_group)
        self.assertEqual(name, 'Test User')

    def test_get_acknowledged_by_name_without_user(self):
        alert_group = Mock()
        alert_group.acknowledged_by = None
        
        serializer = AlertGroupSerializer()
        name = serializer.get_acknowledged_by_name(alert_group)
        self.assertIsNone(name)

    def test_datetime_formatting(self):
        serializer = AlertGroupSerializer(instance=self.alert_group)
        data = serializer.data
        
        # Check datetime formatting
        self.assertRegex(data['first_occurrence'], r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z')
        self.assertRegex(data['last_occurrence'], r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z')
        self.assertRegex(data['acknowledgement_time'], r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z')


class AlertCommentSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
        
        self.alert_group = AlertGroup.objects.create(
            fingerprint='test-fingerprint-123',
            name='Test Alert',
            labels={'severity': 'critical'},
            severity='critical',
            source='prometheus',
            first_occurrence=datetime.now(timezone.utc),
            last_occurrence=datetime.now(timezone.utc),
            current_status='firing'
        )
        
        self.comment = AlertComment.objects.create(
            alert_group=self.alert_group,
            user=self.user,
            content='This is a test comment',
            created_at=datetime.now(timezone.utc)
        )

    def test_comment_serializer_fields(self):
        serializer = AlertCommentSerializer(instance=self.comment)
        data = serializer.data
        
        expected_fields = ['id', 'user_name', 'content', 'created_at']
        
        for field in expected_fields:
            self.assertIn(field, data)

    def test_get_user_name_with_full_name(self):
        serializer = AlertCommentSerializer()
        name = serializer.get_user_name(self.comment)
        self.assertEqual(name, 'Test User')

    def test_get_user_name_without_full_name(self):
        user_no_name = User.objects.create_user(username='noname')
        comment = Mock()
        comment.user = user_no_name
        
        serializer = AlertCommentSerializer()
        name = serializer.get_user_name(comment)
        self.assertEqual(name, 'noname')

    def test_read_only_fields(self):
        serializer = AlertCommentSerializer()
        self.assertIn('alert_group', serializer.Meta.read_only_fields)
        self.assertIn('user', serializer.Meta.read_only_fields)


class AlertmanagerWebhookSerializerTest(TestCase):
    def test_valid_webhook_data(self):
        valid_data = {
            'receiver': 'web.hook',
            'status': 'firing',
            'alerts': [
                {
                    'status': 'firing',
                    'labels': {'alertname': 'InstanceDown'},
                    'annotations': {'description': 'Instance is down'}
                }
            ],
            'groupLabels': {'alertname': 'InstanceDown'},
            'commonLabels': {'job': 'prometheus'},
            'commonAnnotations': {},
            'externalURL': 'http://alertmanager:9093',
            'version': '4',
            'groupKey': 'group-key-123',
            'truncatedAlerts': 0
        }
        
        serializer = AlertmanagerWebhookSerializer(data=valid_data)
        self.assertTrue(serializer.is_valid())

    def test_minimal_webhook_data(self):
        minimal_data = {
            'alerts': [
                {
                    'status': 'firing',
                    'labels': {'alertname': 'TestAlert'}
                }
            ]
        }
        
        serializer = AlertmanagerWebhookSerializer(data=minimal_data)
        self.assertTrue(serializer.is_valid())

    def test_missing_required_field(self):
        invalid_data = {
            'receiver': 'web.hook',
            'status': 'firing'
            # Missing 'alerts' field
        }
        
        serializer = AlertmanagerWebhookSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('alerts', serializer.errors)

    def test_serializer_fields(self):
        serializer = AlertmanagerWebhookSerializer()
        expected_fields = [
            'receiver', 'status', 'alerts', 'groupLabels', 'commonLabels',
            'commonAnnotations', 'externalURL', 'version', 'groupKey', 'truncatedAlerts'
        ]
        
        for field in expected_fields:
            self.assertIn(field, serializer.fields)


class AcknowledgeAlertSerializerTest(TestCase):
    def test_valid_acknowledge_data(self):
        valid_data = {
            'acknowledged': True,
            'comment': 'Acknowledging this alert for investigation'
        }
        
        serializer = AcknowledgeAlertSerializer(data=valid_data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['acknowledged'], True)
        self.assertEqual(serializer.validated_data['comment'], 'Acknowledging this alert for investigation')

    def test_missing_acknowledged_field(self):
        invalid_data = {
            'comment': 'Test comment'
            # Missing 'acknowledged' field
        }
        
        serializer = AcknowledgeAlertSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('acknowledged', serializer.errors)

    def test_missing_comment_field(self):
        invalid_data = {
            'acknowledged': True
            # Missing 'comment' field
        }
        
        serializer = AcknowledgeAlertSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('comment', serializer.errors)

    def test_empty_comment(self):
        invalid_data = {
            'acknowledged': True,
            'comment': ''
        }
        
        serializer = AcknowledgeAlertSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('comment', serializer.errors)

    def test_boolean_validation(self):
        valid_data_false = {
            'acknowledged': False,
            'comment': 'Unacknowledging this alert'
        }
        
        serializer = AcknowledgeAlertSerializer(data=valid_data_false)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['acknowledged'], False)


class SerializerIntegrationTest(TestCase):
    """Integration tests to ensure serializers work together correctly"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
        
        self.alert_group = AlertGroup.objects.create(
            fingerprint='integration-test-123',
            name='Integration Test Alert',
            labels={'severity': 'warning'},
            severity='warning',
            source='prometheus',
            first_occurrence=datetime.now(timezone.utc),
            last_occurrence=datetime.now(timezone.utc),
            current_status='firing'
        )
        
        self.alert_instance = AlertInstance.objects.create(
            alert_group=self.alert_group,
            status='firing',
            started_at=datetime.now(timezone.utc),
            annotations={'description': 'Integration test alert'},
            generator_url='http://prometheus:9090/graph'
        )

    def test_nested_serialization(self):
        """Test that AlertGroupSerializer correctly serializes nested instances"""
        serializer = AlertGroupSerializer(instance=self.alert_group)
        data = serializer.data
        
        # Check that instances are included and properly serialized
        self.assertIn('instances', data)
        self.assertIsInstance(data['instances'], list)
        
        if data['instances']:
            instance_data = data['instances'][0]
            self.assertIn('alert_group_fingerprint', instance_data)
            self.assertEqual(instance_data['alert_group_fingerprint'], 'integration-test-123')

    def test_timezone_consistency(self):
        """Test that all datetime fields are consistently formatted in UTC"""
        group_serializer = AlertGroupSerializer(instance=self.alert_group)
        instance_serializer = AlertInstanceSerializer(instance=self.alert_instance)
        
        group_data = group_serializer.data
        instance_data = instance_serializer.data
        
        # All datetime fields should end with 'Z' indicating UTC
        self.assertTrue(group_data['first_occurrence'].endswith('Z'))
        self.assertTrue(group_data['last_occurrence'].endswith('Z'))
        self.assertTrue(instance_data['started_at'].endswith('Z'))
