from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from alerts.models import AlertGroup, AlertInstance, AlertComment, AlertAcknowledgementHistory
from alerts.api.serializers import (
    AlertInstanceSerializer,
    AlertAcknowledgementHistorySerializer,
    AlertGroupSerializer,
    AlertCommentSerializer,
    AlertmanagerWebhookSerializer,
    AcknowledgeAlertSerializer,
    AlertmanagerAlertSerializer # Added this as it's nested in AlertmanagerWebhookSerializer
)

class AlertInstanceSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123', first_name='Test', last_name='User')
        self.alert_group = AlertGroup.objects.create(
            fingerprint='fp-instance-test',
            name='Test Alert for InstanceSerializer',
            severity='critical',
            current_status='firing',
            acknowledged_by=self.user,
            acknowledgement_time=timezone.now() - timedelta(minutes=30)
        )
        self.alert_instance_firing = AlertInstance.objects.create(
            alert_group=self.alert_group,
            status='firing',
            started_at=timezone.now() - timedelta(hours=1),
            annotations={'summary': 'Instance firing summary', 'description': 'Full description here.'}
        )
        self.alert_instance_resolved = AlertInstance.objects.create(
            alert_group=self.alert_group,
            status='resolved',
            started_at=timezone.now() - timedelta(hours=2),
            ended_at=timezone.now() - timedelta(hours=1, minutes=30),
            annotations={'summary': 'Instance resolved summary'}
        )

    def test_alert_instance_firing_serialization(self):
        serializer = AlertInstanceSerializer(instance=self.alert_instance_firing)
        data = serializer.data
        self.assertEqual(data['id'], self.alert_instance_firing.id)
        self.assertEqual(data['alert_group_fingerprint'], self.alert_group.fingerprint)
        self.assertEqual(data['status'], 'firing')
        self.assertEqual(data['started_at'], self.alert_instance_firing.started_at.isoformat().replace('+00:00', 'Z'))
        self.assertIsNone(data['ended_at']) # Firing instance should have None for ended_at
        self.assertEqual(data['annotations'], self.alert_instance_firing.annotations)

    def test_alert_instance_resolved_serialization(self):
        serializer = AlertInstanceSerializer(instance=self.alert_instance_resolved)
        data = serializer.data
        self.assertEqual(data['id'], self.alert_instance_resolved.id)
        self.assertEqual(data['alert_group_fingerprint'], self.alert_group.fingerprint)
        self.assertEqual(data['status'], 'resolved')
        self.assertEqual(data['started_at'], self.alert_instance_resolved.started_at.isoformat().replace('+00:00', 'Z'))
        self.assertEqual(data['ended_at'], self.alert_instance_resolved.ended_at.isoformat().replace('+00:00', 'Z'))
        self.assertEqual(data['annotations'], self.alert_instance_resolved.annotations)

    def test_alert_instance_deserialization_valid(self):
        """ Basic test for deserialization if it were used. """
        valid_data = {
            'alert_group': self.alert_group.pk, # Assuming alert_group is a PK for write operations
            'status': 'firing',
            'started_at': (timezone.now() - timedelta(minutes=5)).isoformat(),
            'annotations': {'test': 'data'}
        }
        # Note: AlertInstanceSerializer is likely read-only. If it were writable, this would be more relevant.
        # For now, we'll assume it might be used for validation even if not for creation directly.
        serializer = AlertInstanceSerializer(data=valid_data)
        # If it's strictly read-only, is_valid() might be false or raise an error on .save()
        # For this test, let's assume it can validate the structure.
        if serializer.Meta.read_only_fields == '__all__': # A common way to make it fully read-only
             with self.assertRaises(AssertionError): # is_valid() would be false or .save() would fail
                 self.assertTrue(serializer.is_valid(raise_exception=True))
        else:
            # This part of the test might need adjustment based on actual serializer writability
            # If we assume it's NOT read_only_fields = '__all__' for a moment:
            is_valid = serializer.is_valid()
            if not is_valid:
                print("AlertInstanceSerializer deserialization errors (valid data test):", serializer.errors)
            self.assertTrue(is_valid) 
            # self.assertEqual(serializer.validated_data['status'], valid_data['status'])

    def test_alert_instance_deserialization_invalid_missing_status(self):
        invalid_data = {
            'alert_group': self.alert_group.pk,
            'started_at': timezone.now().isoformat(),
            # 'status' is missing
        }
        serializer = AlertInstanceSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('status', serializer.errors)

    def test_alert_ack_history_serialization(self):
        serializer = AlertAcknowledgementHistorySerializer(instance=self.ack_history_entry)
        data = serializer.data
        self.assertEqual(data['id'], self.ack_history_entry.id)
        self.assertEqual(data['alert_group_fingerprint'], self.alert_group.fingerprint)
        self.assertEqual(data['acknowledged_by_username'], self.user.username) # Assuming username is used
        self.assertEqual(data['acknowledged_at'], self.ack_history_entry.acknowledged_at.isoformat().replace('+00:00', 'Z'))
        self.assertEqual(data['comment'], self.ack_history_entry.comment)

    def test_alert_ack_history_deserialization_valid(self):
        """ Basic test for deserialization if it were used. """
        valid_data = {
            'alert_group': self.alert_group.pk,
            'acknowledged_by': self.user.pk,
            'comment': "New ack history entry"
            # acknowledged_at is auto_now_add
        }
        serializer = AlertAcknowledgementHistorySerializer(data=valid_data)
        # Similar to AlertInstanceSerializer, this is likely read-only in practice for API output.
        # Adjusting assertion based on actual implementation.
        if hasattr(serializer.Meta, 'read_only_fields') and serializer.Meta.read_only_fields == '__all__':
            with self.assertRaises(AssertionError): # is_valid() would be false or .save() would fail
                self.assertTrue(serializer.is_valid(raise_exception=True))
        else:
            is_valid = serializer.is_valid()
            if not is_valid:
                print("AckHistorySerializer deserialization errors (valid data):", serializer.errors)
            self.assertTrue(is_valid)
            # self.assertEqual(serializer.validated_data['comment'], valid_data['comment'])

    def test_alert_ack_history_deserialization_invalid_missing_user(self):
        invalid_data = {
            'alert_group': self.alert_group.pk,
            'comment': "Missing user",
            # 'acknowledged_by' is missing
        }
        serializer = AlertAcknowledgementHistorySerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('acknowledged_by', serializer.errors)

    def test_alert_group_firing_serialization(self):
        serializer = AlertGroupSerializer(instance=self.alert_group_firing)
        data = serializer.data

        self.assertEqual(data['fingerprint'], self.alert_group_firing.fingerprint)
        self.assertEqual(data['name'], self.alert_group_firing.name)
        self.assertEqual(data['severity'], self.alert_group_firing.severity)
        self.assertEqual(data['current_status'], self.alert_group_firing.current_status)
        self.assertEqual(data['labels'], self.alert_group_firing.labels)
        self.assertEqual(data['generator_url'], self.alert_group_firing.generator_url)
        self.assertEqual(data['description'], self.alert_group_firing.description)
        self.assertEqual(data['summary'], self.alert_group_firing.summary)
        self.assertEqual(data['first_seen'], self.alert_group_firing.first_seen.isoformat().replace('+00:00', 'Z'))
        self.assertEqual(data['last_seen'], self.alert_group_firing.last_seen.isoformat().replace('+00:00', 'Z'))
        self.assertFalse(data['acknowledged'])
        self.assertIsNone(data['acknowledged_by_username'])
        self.assertIsNone(data['acknowledgement_time'])
        self.assertFalse(data['is_silenced'])
        self.assertEqual(data['instance'], self.alert_group_firing.instance)
        self.assertEqual(data['service'], self.alert_group_firing.service)

        # Check SerializerMethodFields
        self.assertTrue(data['first_seen_display']) # Just check it's populated
        self.assertTrue(data['last_seen_display'])
        self.assertTrue(data['acknowledgement_time_display'] is None or data['acknowledgement_time_display'] == "")


        self.assertEqual(data['total_instances'], 1)
        self.assertEqual(data['active_instances_count'], 1)
        
        # Check nested instances structure (briefly)
        self.assertIn('instances', data)
        self.assertTrue(isinstance(data['instances'], list))
        self.assertEqual(len(data['instances']), 1) # One instance created in setUp for this group
        self.assertIn('status', data['instances'][0])
        self.assertEqual(data['instances'][0]['status'], 'firing')


    def test_alert_group_acked_serialization(self):
        serializer = AlertGroupSerializer(instance=self.alert_group_acked)
        data = serializer.data

        self.assertEqual(data['fingerprint'], self.alert_group_acked.fingerprint)
        self.assertTrue(data['acknowledged'])
        self.assertEqual(data['acknowledged_by_username'], self.user.username) # or get_full_name() depending on serializer
        self.assertIsNotNone(data['acknowledgement_time'])
        self.assertEqual(data['acknowledgement_time'], self.alert_group_acked.acknowledgement_time.isoformat().replace('+00:00', 'Z'))
        self.assertTrue(data['acknowledgement_time_display']) # Should be populated
        self.assertTrue(data['is_silenced'])
        
        self.assertEqual(data['total_instances'], 1)
        self.assertEqual(data['active_instances_count'], 0) # Resolved instance
        self.assertEqual(len(data['instances']), 1)
        self.assertEqual(data['instances'][0]['status'], 'resolved')

    def test_alert_group_deserialization_valid_read_only_nature(self):
        """ AlertGroupSerializer is primarily read-only. Test basic validation if any writeable fields existed. """
        # Assuming most fields are read-only or derived.
        # If there were writable fields, we'd test them here.
        # Example: if 'name' was writable:
        valid_data = {'fingerprint': 'fp-new', 'name': 'New Name From Test'} 
        serializer = AlertGroupSerializer(data=valid_data)
        # is_valid() will likely be False because many fields are read-only or required from model.
        # This test is more conceptual for a read-only serializer.
        # If we were to create/update, we'd mock the instance or provide all required model fields.
        self.assertFalse(serializer.is_valid()) 
        self.assertIn('severity', serializer.errors) # Required model field
        self.assertIn('current_status', serializer.errors) # Required model field

    def test_alert_group_deserialization_invalid_severity_choice(self):
        # Test if severity had choices and an invalid one was provided
        invalid_data = {
            'fingerprint': 'fp-invalid-sev',
            'name': 'Invalid Severity Test',
            'severity': 'super-critical', # Assuming this is not a valid choice
            'current_status': 'firing',
            'labels': {}, 'generator_url': '', 'description': '', 'summary': '',
            'first_seen': timezone.now().isoformat(), 'last_seen': timezone.now().isoformat()
        }
        serializer = AlertGroupSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('severity', serializer.errors)
        self.assertIn('"super-critical" is not a valid choice.', str(serializer.errors['severity']))

    def test_alert_comment_serialization(self):
        serializer = AlertCommentSerializer(instance=self.comment)
        data = serializer.data
        self.assertEqual(data['id'], self.comment.id)
        self.assertEqual(data['alert_group_fingerprint'], self.alert_group_for_comment.fingerprint)
        self.assertEqual(data['user_username'], self.user_commenter.username) # or get_full_name()
        self.assertTrue(data['created_at_display']) # Check it's populated
        self.assertEqual(data['content'], self.comment.content)

    def test_alert_comment_deserialization_valid(self):
        valid_data = {
            'content': "A new valid comment via serializer.",
            # alert_group and user would be typically set by the view/context
        }
        # To test create, we need to simulate the context that the view would provide
        serializer_context = {
            'alert_group': self.alert_group_for_comment,
            'user': self.user_commenter 
        }
        serializer = AlertCommentSerializer(data=valid_data, context=serializer_context)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        self.assertEqual(serializer.validated_data['content'], valid_data['content'])

    def test_alert_comment_deserialization_invalid_empty_content(self):
        invalid_data = {'content': ""}
        serializer = AlertCommentSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('content', serializer.errors)
        self.assertIn('This field may not be blank.', str(serializer.errors['content']))

    def test_alert_comment_deserialization_invalid_missing_content(self):
        invalid_data = {} # content is missing
        serializer = AlertCommentSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('content', serializer.errors)
        self.assertIn('This field is required.', str(serializer.errors['content']))

    def test_alert_comment_create_method(self):
        valid_data = {'content': "Comment created by .create()"}
        serializer_context = {
            'alert_group': self.alert_group_for_comment,
            'user': self.user_commenter
        }
        serializer = AlertCommentSerializer(data=valid_data, context=serializer_context)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        
        comment_instance = serializer.save() # .save() will call .create()
        
        self.assertIsNotNone(comment_instance)
        self.assertEqual(comment_instance.content, valid_data['content'])
        self.assertEqual(comment_instance.alert_group, self.alert_group_for_comment)
        self.assertEqual(comment_instance.user, self.user_commenter)
        self.assertTrue(AlertComment.objects.filter(id=comment_instance.id).exists())

    def test_alertmanager_webhook_serializer_valid(self):
        serializer = AlertmanagerWebhookSerializer(data=self.valid_payload)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        validated_data = serializer.validated_data
        self.assertEqual(validated_data['version'], self.valid_payload['version'])
        self.assertEqual(validated_data['status'], self.valid_payload['status'])
        self.assertEqual(len(validated_data['alerts']), len(self.valid_payload['alerts']))
        # Check structure of a nested alert
        self.assertEqual(validated_data['alerts'][0]['labels'], self.valid_payload['alerts'][0]['labels'])

    def test_alertmanager_webhook_serializer_missing_version(self):
        payload = self.valid_payload.copy()
        del payload['version']
        serializer = AlertmanagerWebhookSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn('version', serializer.errors)

    def test_alertmanager_webhook_serializer_missing_alerts_list(self):
        payload = self.valid_payload.copy()
        del payload['alerts']
        serializer = AlertmanagerWebhookSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn('alerts', serializer.errors)

    def test_alertmanager_webhook_serializer_empty_alerts_list(self):
        # Alertmanager can send an empty alerts list, which should be valid for the webhook
        # if the main structure is okay. The processing task would then handle no alerts.
        payload = self.valid_payload.copy()
        payload['alerts'] = []
        serializer = AlertmanagerWebhookSerializer(data=payload)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        self.assertEqual(len(serializer.validated_data['alerts']), 0)
        
    def test_alertmanager_webhook_serializer_invalid_alert_item_missing_labels(self):
        payload = self.valid_payload.copy()
        # Modify the first alert to be invalid (e.g., missing 'labels')
        del payload['alerts'][0]['labels']
        serializer = AlertmanagerWebhookSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn('alerts', serializer.errors)
        # Errors for nested serializers are typically lists of dicts
        self.assertTrue(isinstance(serializer.errors['alerts'], list))
        self.assertTrue(isinstance(serializer.errors['alerts'][0], dict))
        self.assertIn('labels', serializer.errors['alerts'][0])
        self.assertIn('This field is required.', str(serializer.errors['alerts'][0]['labels']))

    def test_alertmanager_webhook_serializer_invalid_alert_item_bad_startsAt_format(self):
        payload = self.valid_payload.copy()
        payload['alerts'][0]['startsAt'] = "not-a-datetime"
        serializer = AlertmanagerWebhookSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn('alerts', serializer.errors)
        self.assertIn('startsAt', serializer.errors['alerts'][0])
        self.assertIn('Invalid isoformat string', str(serializer.errors['alerts'][0]['startsAt']))

    def test_acknowledge_alert_serializer_valid_true(self):
        valid_data = {'acknowledged': True, 'comment': "Acknowledging this alert."}
        serializer = AcknowledgeAlertSerializer(data=valid_data)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        self.assertTrue(serializer.validated_data['acknowledged'])
        self.assertEqual(serializer.validated_data['comment'], "Acknowledging this alert.")

    def test_acknowledge_alert_serializer_valid_false(self):
        valid_data = {'acknowledged': False, 'comment': "Un-acknowledging the alert."}
        serializer = AcknowledgeAlertSerializer(data=valid_data)
        self.assertTrue(serializer.is_valid(raise_exception=True))
        self.assertFalse(serializer.validated_data['acknowledged'])
        self.assertEqual(serializer.validated_data['comment'], "Un-acknowledging the alert.")

    def test_acknowledge_alert_serializer_missing_acknowledged(self):
        invalid_data = {'comment': "Missing ack field."}
        serializer = AcknowledgeAlertSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('acknowledged', serializer.errors)
        self.assertIn('This field is required.', str(serializer.errors['acknowledged']))

    def test_acknowledge_alert_serializer_missing_comment(self):
        invalid_data = {'acknowledged': True}
        serializer = AcknowledgeAlertSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('comment', serializer.errors)
        self.assertIn('This field is required.', str(serializer.errors['comment']))

    def test_acknowledge_alert_serializer_empty_comment(self):
        invalid_data = {'acknowledged': True, 'comment': ""}
        serializer = AcknowledgeAlertSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('comment', serializer.errors)
        self.assertIn('This field may not be blank.', str(serializer.errors['comment']))
        
    def test_acknowledge_alert_serializer_whitespace_comment(self):
        # Assuming the serializer doesn't allow only whitespace, which is good practice.
        # If it does, this test would need to change or be removed.
        invalid_data = {'acknowledged': True, 'comment': "   "}
        serializer = AcknowledgeAlertSerializer(data=invalid_data)
        # Default DRF CharField with allow_blank=False trim_whitespace=True would make this invalid
        # if after trimming it's empty. If trim_whitespace=False, "   " is valid.
        # Let's assume it's effectively required to be non-blank after trim.
        self.assertFalse(serializer.is_valid()) 
        self.assertIn('comment', serializer.errors)
        # The exact error message might vary based on field definition (e.g. if a validator is used)
        # "This field may not be blank." is common for allow_blank=False

    def test_acknowledge_alert_serializer_non_boolean_acknowledged(self):
        invalid_data = {'acknowledged': "not-a-bool", 'comment': "Valid comment."}
        serializer = AcknowledgeAlertSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('acknowledged', serializer.errors)
        self.assertIn('Must be a valid boolean.', str(serializer.errors['acknowledged']))


class AlertAcknowledgementHistorySerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='ackuser', password='password123', first_name='Ack', last_name='User')
        self.alert_group = AlertGroup.objects.create(
            fingerprint='fp-ackhistory-test',
            name='Test Alert for AckHistorySerializer',
            severity='warning'
        )
        self.ack_history_entry = AlertAcknowledgementHistory.objects.create(
            alert_group=self.alert_group,
            acknowledged_by=self.user,
            comment="Initial acknowledgement for testing."
        )

class AlertGroupSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='groupuser', password='password123', first_name='Group', last_name='Test')
        self.alert_group_firing = AlertGroup.objects.create(
            fingerprint='fp-group-firing', name='Group Firing Test', severity='critical', current_status='firing',
            labels={'job': 'node', 'instance': 'serverA'}, generator_url='http://prom/g0',
            description='This is a firing alert group.', summary='Firing Group Summary',
            first_seen=timezone.now() - timedelta(days=1), last_seen=timezone.now(),
            acknowledged=False, is_silenced=False
        )
        self.alert_group_acked = AlertGroup.objects.create(
            fingerprint='fp-group-acked', name='Group Acked Test', severity='warning', current_status='resolved',
            labels={'job': 'db', 'instance': 'serverB'},
            acknowledged=True, acknowledged_by=self.user, acknowledgement_time=timezone.now() - timedelta(hours=1),
            is_silenced=True
        )
        # Add instances for nested serialization
        AlertInstance.objects.create(alert_group=self.alert_group_firing, status='firing', started_at=timezone.now()-timedelta(hours=1))
        AlertInstance.objects.create(alert_group=self.alert_group_acked, status='resolved', started_at=timezone.now()-timedelta(hours=2), ended_at=timezone.now()-timedelta(hours=1))

class AlertCommentSerializerTests(TestCase):
    def setUp(self):
        self.user_commenter = User.objects.create_user(username='commenter', password='password123', first_name='Comment', last_name='User')
        self.alert_group_for_comment = AlertGroup.objects.create(
            fingerprint='fp-comment-test',
            name='Test Alert for CommentSerializer',
            severity='info'
        )
        self.comment = AlertComment.objects.create(
            alert_group=self.alert_group_for_comment,
            user=self.user_commenter,
            content="This is a test comment."
        )

class AlertmanagerWebhookSerializerTests(TestCase):
    def setUp(self):
        self.valid_payload = {
            "version": "4",
            "groupKey": "{}:{alertname=\"HighCPUUsage\"}",
            "truncatedAlerts": 0,
            "status": "firing", # or "resolved"
            "receiver": "webhook-receiver",
            "groupLabels": {"alertname": "HighCPUUsage"},
            "commonLabels": {"alertname": "HighCPUUsage", "severity": "critical"},
            "commonAnnotations": {"summary": "High CPU usage detected"},
            "externalURL": "http://alertmanager.example.com",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {"alertname": "HighCPUUsage", "instance": "server1"},
                    "annotations": {"summary": "CPU usage on server1 > 90%"},
                    "startsAt": "2023-10-27T10:00:00Z",
                    "endsAt": "0001-01-01T00:00:00Z",
                    "generatorURL": "http://prometheus/graph",
                    "fingerprint": "fp123"
                },
                {
                    "status": "resolved",
                    "labels": {"alertname": "HighCPUUsage", "instance": "server2"},
                    "annotations": {"summary": "CPU usage on server2 resolved"},
                    "startsAt": "2023-10-27T09:00:00Z",
                    "endsAt": "2023-10-27T09:30:00Z", # Resolved alert has an end time
                    "generatorURL": "http://prometheus/graph2",
                    "fingerprint": "fp456"
                }
            ]
        }

class AcknowledgeAlertSerializerTests(TestCase):
    def setUp(self):
        # This serializer is simple, primarily for validation. No complex setup needed.
        pass

# Placeholder for AlertmanagerAlertSerializer tests if directly needed,
# but it's mostly tested via AlertmanagerWebhookSerializer.
# class AlertmanagerAlertSerializerTests(TestCase):
#     pass

# Test methods will be added in subsequent steps.
