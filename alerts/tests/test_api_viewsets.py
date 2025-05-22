import json
from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from unittest.mock import patch

from alerts.models import AlertGroup, AlertInstance, AlertComment, AlertAcknowledgementHistory
from alerts.api.serializers import AlertGroupSerializer, AlertInstanceSerializer, AlertCommentSerializer

User = get_user_model()

class AlertGroupViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.admin_user = User.objects.create_superuser(username='adminuser', password='adminpassword', email='admin@example.com')
        self.client.force_authenticate(user=self.user)

        self.alert_group_1 = AlertGroup.objects.create(
            fingerprint='fg1',
            name='Test Alert 1',
            labels={'alertname': 'TestAlert1', 'severity': 'critical', 'instance': 'host1', 'service': 'web', 'job': 'nginx', 'cluster': 'prod', 'namespace': 'default'},
            severity='critical',
            current_status='firing',
            instance='host1',
            source='alertmanager',
            total_firing_count=1
        )
        self.alert_instance_1_1 = AlertInstance.objects.create(
            alert_group=self.alert_group_1,
            status='firing',
            started_at=timezone.now() - timedelta(minutes=10),
            annotations={'summary': 'Alert 1 firing'},
            generator_url='http://example.com/alert1'
        )
        self.alert_instance_1_2 = AlertInstance.objects.create(
            alert_group=self.alert_group_1,
            status='resolved',
            started_at=timezone.now() - timedelta(minutes=20),
            ended_at=timezone.now() - timedelta(minutes=15),
            annotations={'summary': 'Alert 1 resolved'},
            generator_url='http://example.com/alert1'
        )
        AlertComment.objects.create(
            alert_group=self.alert_group_1,
            user=self.user,
            content="Initial comment for alert 1"
        )

        self.alert_group_2 = AlertGroup.objects.create(
            fingerprint='fg2',
            name='Test Alert 2',
            labels={'alertname': 'TestAlert2', 'severity': 'warning', 'instance': 'host2', 'service': 'db', 'job': 'mysql', 'cluster': 'dev', 'namespace': 'staging'},
            severity='warning',
            current_status='resolved',
            instance='host2',
            source='alertmanager',
            total_firing_count=1
        )
        self.alert_instance_2_1 = AlertInstance.objects.create(
            alert_group=self.alert_group_2,
            status='resolved',
            started_at=timezone.now() - timedelta(minutes=5),
            ended_at=timezone.now(),
            annotations={'summary': 'Alert 2 resolved'},
            generator_url='http://example.com/alert2'
        )

        self.list_url = '/alerts/api/v1/alerts/'
        self.detail_url = f'/alerts/api/v1/alerts/{self.alert_group_1.fingerprint}/'
        self.acknowledge_url = f'/alerts/api/v1/alerts/{self.alert_group_1.fingerprint}/acknowledge/'
        self.history_url = f'/alerts/api/v1/alerts/{self.alert_group_1.fingerprint}/history/'
        self.comments_url = f'/alerts/api/v1/alerts/{self.alert_group_1.fingerprint}/comments/'

    def test_list_alert_groups_no_filters(self):
        """
        Ensure we can retrieve a list of alert groups, showing only active (firing) by default.
        """
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1) # Only alert_group_1 is firing
        self.assertEqual(response.data['results'][0]['fingerprint'], self.alert_group_1.fingerprint)

    def test_list_alert_groups_active_only_false(self):
        """
        Ensure we can retrieve all alert groups when active_only is false.
        """
        response = self.client.get(self.list_url + '?active_only=false')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        fingerprints = [ag['fingerprint'] for ag in response.data['results']]
        self.assertIn(self.alert_group_1.fingerprint, fingerprints)
        self.assertIn(self.alert_group_2.fingerprint, fingerprints)

    def test_list_alert_groups_filter_by_status(self):
        """
        Ensure we can filter alert groups by current_status.
        """
        response = self.client.get(self.list_url + '?status=resolved')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['fingerprint'], self.alert_group_2.fingerprint)
        self.assertEqual(response.data['results'][0]['current_status'], 'resolved')

    def test_list_alert_groups_filter_by_instance(self):
        """
        Ensure we can filter alert groups by instance.
        """
        response = self.client.get(self.list_url + '?instance=host1&active_only=false')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['fingerprint'], self.alert_group_1.fingerprint)

    def test_list_alert_groups_filter_by_service(self):
        """
        Ensure we can filter alert groups by service.
        """
        response = self.client.get(self.list_url + '?service=web&active_only=false')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['fingerprint'], self.alert_group_1.fingerprint)

    def test_list_alert_groups_filter_by_job(self):
        """
        Ensure we can filter alert groups by job.
        """
        response = self.client.get(self.list_url + '?job=nginx&active_only=false')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['fingerprint'], self.alert_group_1.fingerprint)

    def test_list_alert_groups_filter_by_cluster(self):
        """
        Ensure we can filter alert groups by cluster.
        """
        response = self.client.get(self.list_url + '?cluster=prod&active_only=false')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['fingerprint'], self.alert_group_1.fingerprint)

    def test_list_alert_groups_filter_by_namespace(self):
        """
        Ensure we can filter alert groups by namespace.
        """
        response = self.client.get(self.list_url + '?namespace=default&active_only=false')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['fingerprint'], self.alert_group_1.fingerprint)

    def test_retrieve_alert_group(self):
        """
        Ensure we can retrieve a single alert group by fingerprint.
        """
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['fingerprint'], self.alert_group_1.fingerprint)
        self.assertIn('instances', response.data)
        self.assertIn('acknowledgement_history', response.data)

    @patch('alerts.api.views.acknowledge_alert') # Corrected patch target
    def test_acknowledge_alert_group_true(self, mock_acknowledge_alert):
        """
        Ensure an alert group can be acknowledged.
        """
        self.client.force_authenticate(user=self.admin_user)
        data = {'acknowledged': True, 'comment': 'Acknowledging this alert'}
        response = self.client.put(self.acknowledge_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        mock_acknowledge_alert.assert_called_once_with(self.alert_group_1, self.admin_user, data['comment'])
        self.assertTrue(AlertComment.objects.filter(alert_group=self.alert_group_1, content=data['comment']).exists())

    @patch('alerts.services.alerts_processor.acknowledge_alert')
    def test_acknowledge_alert_group_false(self, mock_acknowledge_alert):
        """
        Ensure an alert group can be un-acknowledged.
        """
        # First acknowledge it
        self.alert_group_1.acknowledged = True
        self.alert_group_1.acknowledged_by = self.admin_user
        self.alert_group_1.acknowledgement_time = timezone.now()
        self.alert_group_1.save()

        self.client.force_authenticate(user=self.admin_user)
        data = {'acknowledged': False, 'comment': 'Un-acknowledging this alert'}
        response = self.client.put(self.acknowledge_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.alert_group_1.refresh_from_db()
        self.assertFalse(self.alert_group_1.acknowledged)
        # acknowledged_by and acknowledgement_time should remain from the last acknowledgement
        self.assertIsNotNone(self.alert_group_1.acknowledged_by)
        self.assertIsNotNone(self.alert_group_1.acknowledgement_time)
        mock_acknowledge_alert.assert_not_called() # acknowledge_alert is only called for True
        self.assertTrue(AlertComment.objects.filter(alert_group=self.alert_group_1, content=f"Alert un-acknowledged: {data['comment']}").exists())

    def test_acknowledge_alert_group_invalid_data(self):
        """
        Ensure acknowledging with invalid data returns a bad request.
        """
        self.client.force_authenticate(user=self.admin_user)
        data = {'acknowledged': True} # Missing comment
        response = self.client.put(self.acknowledge_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('comment', response.data)

    def test_history_action(self):
        """
        Ensure the history action returns all instances for an alert group.
        """
        response = self.client.get(self.history_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2) # Two instances for alert_group_1
        serializer = AlertInstanceSerializer(self.alert_group_1.instances.all(), many=True)
        self.assertEqual(response.data, serializer.data)

    def test_comments_action_get(self):
        """
        Ensure the comments action (GET) returns all comments for an alert group.
        """
        response = self.client.get(self.comments_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1) # One initial comment
        serializer = AlertCommentSerializer(self.alert_group_1.comments.all(), many=True)
        self.assertEqual(response.data, serializer.data)

    def test_comments_action_post_valid(self):
        """
        Ensure the comments action (POST) can create a new comment.
        """
        self.client.force_authenticate(user=self.admin_user)
        data = {'content': 'This is a new comment.'}
        response = self.client.post(self.comments_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AlertComment.objects.filter(alert_group=self.alert_group_1).count(), 2)
        self.assertEqual(response.data['content'], data['content'])
        self.assertEqual(response.data['user_name'], self.admin_user.username) # Check user_name instead of user ID

    def test_comments_action_post_invalid(self):
        """
        Ensure the comments action (POST) with invalid data returns a bad request.
        """
        self.client.force_authenticate(user=self.admin_user)
        data = {'content': ''} # Empty content
        response = self.client.post(self.comments_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('content', response.data)