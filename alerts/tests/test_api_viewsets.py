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

class AlertHistoryViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_authenticate(user=self.user)

        self.alert_group_1 = AlertGroup.objects.create(
            fingerprint='fg_history_1',
            name='History Test Alert 1',
            labels={}, # Added labels field
            severity='critical',
            current_status='firing',
            instance='host_history_1',
            source='alertmanager',
            total_firing_count=1
        )
        self.alert_group_2 = AlertGroup.objects.create(
            fingerprint='fg_history_2',
            name='History Test Alert 2',
            labels={}, # Added labels field
            severity='warning',
            current_status='resolved',
            instance='host_history_2',
            source='alertmanager',
            total_firing_count=1
        )

        # Instances for alert_group_1
        self.instance_1_firing = AlertInstance.objects.create(
            alert_group=self.alert_group_1,
            status='firing',
            started_at=timezone.make_aware(timezone.datetime(2025, 5, 18, 0, 0, 0)) - timedelta(days=5),
            annotations={'summary': 'Instance 1 firing'}
        )
        self.instance_1_resolved_old = AlertInstance.objects.create(
            alert_group=self.alert_group_1,
            status='resolved',
            started_at=timezone.make_aware(timezone.datetime(2025, 5, 18, 0, 0, 0)) - timedelta(days=10),
            ended_at=timezone.make_aware(timezone.datetime(2025, 5, 18, 0, 0, 0)) - timedelta(days=9),
            annotations={'summary': 'Instance 1 resolved old'}
        )
        self.instance_1_resolved_recent = AlertInstance.objects.create(
            alert_group=self.alert_group_1,
            status='resolved',
            started_at=timezone.make_aware(timezone.datetime(2025, 5, 18, 0, 0, 0)) - timedelta(days=2),
            ended_at=timezone.make_aware(timezone.datetime(2025, 5, 18, 0, 0, 0)) - timedelta(days=1),
            annotations={'summary': 'Instance 1 resolved recent'}
        )

        # Instances for alert_group_2
        self.instance_2_firing = AlertInstance.objects.create(
            alert_group=self.alert_group_2,
            status='firing',
            started_at=timezone.make_aware(timezone.datetime(2025, 5, 18, 0, 0, 0)) - timedelta(days=3),
            annotations={'summary': 'Instance 2 firing'}
        )
        self.instance_2_resolved = AlertInstance.objects.create(
            alert_group=self.alert_group_2,
            status='resolved',
            started_at=timezone.make_aware(timezone.datetime(2025, 5, 18, 0, 0, 0)) - timedelta(days=7),
            ended_at=timezone.make_aware(timezone.datetime(2025, 5, 18, 0, 0, 0)) - timedelta(days=6),
            annotations={'summary': 'Instance 2 resolved'}
        )

        self.list_url = reverse('alerts:history-list')

    def test_list_all_alert_instances(self):
        """
        Ensure we can retrieve a list of all alert instances.
        """
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), AlertInstance.objects.count())
        # Verify that the serializer is working as expected
        serializer = AlertInstanceSerializer(AlertInstance.objects.all().order_by('-started_at'), many=True)
        self.assertEqual(response.data['results'], serializer.data)

    def test_filter_by_status(self):
        """
        Ensure we can filter alert instances by status.
        """
        response = self.client.get(self.list_url + '?status=firing')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2) # instance_1_firing, instance_2_firing
        statuses = [inst['status'] for inst in response.data['results']]
        self.assertTrue(all(s == 'firing' for s in statuses))

        response = self.client.get(self.list_url + '?status=resolved')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 3) # instance_1_resolved_old, instance_1_resolved_recent, instance_2_resolved
        statuses = [inst['status'] for inst in response.data['results']]
        self.assertTrue(all(s == 'resolved' for s in statuses))

    def test_filter_by_fingerprint(self):
        """
        Ensure we can filter alert instances by alert group fingerprint.
        """
        response = self.client.get(self.list_url + f'?fingerprint={self.alert_group_1.fingerprint}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 3) # All instances for alert_group_1
        alert_group_fingerprints = [inst['alert_group_fingerprint'] for inst in response.data['results']]
        self.assertTrue(all(f == self.alert_group_1.fingerprint for f in alert_group_fingerprints))

        response = self.client.get(self.list_url + f'?fingerprint={self.alert_group_2.fingerprint}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2) # All instances for alert_group_2
        alert_group_fingerprints = [inst['alert_group_fingerprint'] for inst in response.data['results']]
        self.assertTrue(all(f == self.alert_group_2.fingerprint for f in alert_group_fingerprints))

    def test_filter_by_start_date(self):
        """
        Ensure we can filter alert instances by started_at (gte).
        """
        # Get instances started on or after 2025-05-14 (instance_1_resolved_recent, instance_2_firing)
        start_datetime = timezone.make_aware(timezone.datetime(2025, 5, 18, 0, 0, 0)) - timedelta(days=4)
        response = self.client.get(self.list_url, {'start_date': start_datetime})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2) # Corrected expected count
        instance_ids = {inst['id'] for inst in response.data['results']}
        self.assertNotIn(self.instance_1_firing.id, instance_ids) # Corrected assertion
        self.assertIn(self.instance_2_firing.id, instance_ids)
        self.assertIn(self.instance_1_resolved_recent.id, instance_ids)
        self.assertNotIn(self.instance_1_resolved_old.id, instance_ids)
        self.assertNotIn(self.instance_2_resolved.id, instance_ids)

    def test_filter_by_end_date(self):
        """
        Ensure we can filter alert instances by started_at (lte).
        """
        # Get instances started on or before 2025-05-12 (instance_1_resolved_old, instance_2_resolved)
        end_datetime = timezone.make_aware(timezone.datetime(2025, 5, 18, 0, 0, 0)) - timedelta(days=6)
        response = self.client.get(self.list_url, {'end_date': end_datetime})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        instance_ids = {inst['id'] for inst in response.data['results']}
        self.assertIn(self.instance_1_resolved_old.id, instance_ids)
        self.assertIn(self.instance_2_resolved.id, instance_ids)
        self.assertNotIn(self.instance_1_firing.id, instance_ids)
        self.assertNotIn(self.instance_1_resolved_recent.id, instance_ids)
        self.assertNotIn(self.instance_2_firing.id, instance_ids)

    def test_filter_by_fingerprint_and_status(self):
        """
        Ensure we can filter by both fingerprint and status.
        """
        response = self.client.get(self.list_url + f'?fingerprint={self.alert_group_1.fingerprint}&status=firing')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], self.instance_1_firing.id)

        response = self.client.get(self.list_url + f'?fingerprint={self.alert_group_1.fingerprint}&status=resolved')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        instance_ids = {inst['id'] for inst in response.data['results']}
        self.assertIn(self.instance_1_resolved_old.id, instance_ids)
        self.assertIn(self.instance_1_resolved_recent.id, instance_ids)

    def test_filter_by_date_range(self):
        """
        Ensure we can filter by a date range (start_date and end_date).
        """
        # Instances started between 2025-05-12 and 2025-05-15 (instance_1_firing, instance_2_firing)
        start_datetime = timezone.make_aware(timezone.datetime(2025, 5, 18, 0, 0, 0)) - timedelta(days=6)
        end_datetime = timezone.make_aware(timezone.datetime(2025, 5, 18, 0, 0, 0)) - timedelta(days=3)
        response = self.client.get(self.list_url, {
            'start_date': start_datetime,
            'end_date': end_datetime
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2) # Corrected expected count
        instance_ids = {inst['id'] for inst in response.data['results']}
        self.assertIn(self.instance_1_firing.id, instance_ids)
        self.assertIn(self.instance_2_firing.id, instance_ids)
        self.assertNotIn(self.instance_2_resolved.id, instance_ids) # Corrected assertion
        self.assertNotIn(self.instance_1_resolved_old.id, instance_ids)
        self.assertNotIn(self.instance_1_resolved_recent.id, instance_ids)

    def test_no_matching_results(self):
        """
        Ensure an empty list is returned when no instances match the filters.
        """
        response = self.client.get(self.list_url + '?status=nonexistent')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', response.data) # Expecting validation error details

        response = self.client.get(self.list_url + '?fingerprint=nonexistent_fg')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)

    def test_unauthenticated_access(self):
        """
        Ensure unauthenticated users cannot access the AlertHistoryViewSet.
        """
        self.client.force_authenticate(user=None) # Unauthenticate the client
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)