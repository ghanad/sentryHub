import json
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

# Assuming tasks.py is in the 'alerts' app
# from ..tasks import process_alert_payload_task # Will be mocked

class AlertWebhookViewTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.webhook_url = reverse('alerts_api:alert-webhook') # Assuming 'alerts_api' is the namespace

        self.valid_payload = {
            "version": "4",
            "groupKey": "{}:{alertname=\"HighCPUUsage\"}",
            "truncatedAlerts": 0,
            "status": "firing",
            "receiver": "webhook-receiver",
            "groupLabels": {"alertname": "HighCPUUsage"},
            "commonLabels": {"alertname": "HighCPUUsage", "severity": "critical", "job": "node_exporter"},
            "commonAnnotations": {"summary": "High CPU usage detected on instance X"},
            "externalURL": "http://alertmanager.example.com",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "HighCPUUsage",
                        "instance": "server1",
                        "severity": "critical",
                        "job": "node_exporter"
                    },
                    "annotations": {
                        "summary": "High CPU usage on server1",
                        "description": "CPU usage on server1 is above 90%."
                    },
                    "startsAt": "2023-10-26T10:00:00Z",
                    "endsAt": "0001-01-01T00:00:00Z", # Prometheus way of saying 'not ended'
                    "generatorURL": "http://prometheus.example.com/graph?g0.expr=...",
                    "fingerprint": "fingerprint123"
                }
            ]
        }

class AlertHistoryViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='historytestuser', password='password123')
        self.list_url = reverse('alerts_api:alerthistory-list') # Default DRF naming for list

        self.ag1 = AlertGroup.objects.create(
            fingerprint='historyfp1', name='History Alert Group 1', severity='critical', current_status='firing'
        )
        self.ag2 = AlertGroup.objects.create(
            fingerprint='historyfp2', name='History Alert Group 2', severity='warning', current_status='resolved'
        )

        self.now = timezone.now()
        self.instance1_ag1_firing = AlertInstance.objects.create(
            alert_group=self.ag1, status='firing', 
            started_at=self.now - timedelta(days=2),
            annotations={'summary': 'AG1 Firing Instance 1 (2 days ago)'}
        )
        self.instance2_ag1_resolved = AlertInstance.objects.create(
            alert_group=self.ag1, status='resolved',
            started_at=self.now - timedelta(days=1), ended_at=self.now - timedelta(hours=12),
            annotations={'summary': 'AG1 Resolved Instance 2 (1 day ago)'}
        )
        self.instance3_ag2_firing = AlertInstance.objects.create(
            alert_group=self.ag2, status='firing',
            started_at=self.now - timedelta(hours=6),
            annotations={'summary': 'AG2 Firing Instance 3 (6 hours ago)'}
        )
        self.instance4_ag2_resolved = AlertInstance.objects.create(
            alert_group=self.ag2, status='resolved',
            started_at=self.now - timedelta(hours=2), ended_at=self.now - timedelta(hours=1),
            annotations={'summary': 'AG2 Resolved Instance 4 (2 hours ago)'}
        )
        
        # URLs for retrieve action
        self.detail_url_i1 = reverse('alerts_api:alerthistory-detail', kwargs={'pk': self.instance1_ag1_firing.pk})
        self.detail_url_i3 = reverse('alerts_api:alerthistory-detail', kwargs={'pk': self.instance3_ag2_firing.pk})

    # --- List Action Tests (GET /history/) ---
    def test_list_history_unauthenticated(self):
        """Test listing alert history by an unauthenticated user."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_history_authenticated(self):
        """Test listing all alert history for an authenticated user."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 4) # Total instances created
        self.assertEqual(len(response.data['results']), 4) # Default page size might be larger

    def test_list_history_filter_by_status_firing(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url, {'status': 'firing'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        pks_in_response = {item['id'] for item in response.data['results']}
        self.assertIn(self.instance1_ag1_firing.pk, pks_in_response)
        self.assertIn(self.instance3_ag2_firing.pk, pks_in_response)

    def test_list_history_filter_by_status_resolved(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url, {'status': 'resolved'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        pks_in_response = {item['id'] for item in response.data['results']}
        self.assertIn(self.instance2_ag1_resolved.pk, pks_in_response)
        self.assertIn(self.instance4_ag2_resolved.pk, pks_in_response)

    def test_list_history_filter_by_fingerprint(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url, {'fingerprint': self.ag1.fingerprint})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        pks_in_response = {item['id'] for item in response.data['results']}
        self.assertIn(self.instance1_ag1_firing.pk, pks_in_response)
        self.assertIn(self.instance2_ag1_resolved.pk, pks_in_response)

    def test_list_history_filter_by_start_date(self):
        """Test filtering by start_date (gte started_at)."""
        self.client.force_authenticate(user=self.user)
        # Filter for instances started from 1 day ago (should include i2_ag1, i3_ag2, i4_ag2)
        start_date_filter = (self.now - timedelta(days=1)).isoformat()
        response = self.client.get(self.list_url, {'start_date': start_date_filter})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)
        pks_in_response = {item['id'] for item in response.data['results']}
        self.assertNotIn(self.instance1_ag1_firing.pk, pks_in_response) # Started 2 days ago
        self.assertIn(self.instance2_ag1_resolved.pk, pks_in_response)
        self.assertIn(self.instance3_ag2_firing.pk, pks_in_response)
        self.assertIn(self.instance4_ag2_resolved.pk, pks_in_response)

    def test_list_history_filter_by_end_date(self):
        """Test filtering by end_date (lte started_at)."""
        self.client.force_authenticate(user=self.user)
        # Filter for instances started_at up to 1 day ago (should include i1_ag1)
        # This means started_at <= (now - 1 day)
        end_date_filter = (self.now - timedelta(days=1)).isoformat()
        response = self.client.get(self.list_url, {'end_date': end_date_filter})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2) # i1_ag1 and i2_ag1
        pks_in_response = {item['id'] for item in response.data['results']}
        self.assertIn(self.instance1_ag1_firing.pk, pks_in_response) # Started 2 days ago
        self.assertIn(self.instance2_ag1_resolved.pk, pks_in_response) # Started 1 day ago
        self.assertNotIn(self.instance3_ag2_firing.pk, pks_in_response) # Started 6 hours ago
        self.assertNotIn(self.instance4_ag2_resolved.pk, pks_in_response) # Started 2 hours ago
        
    def test_list_history_filter_by_date_range(self):
        """Test filtering by both start_date and end_date."""
        self.client.force_authenticate(user=self.user)
        # Instances started between 7 hours ago and 3 hours ago (should only include i3_ag2)
        start_filter = (self.now - timedelta(hours=7)).isoformat()
        end_filter = (self.now - timedelta(hours=3)).isoformat() # started_at <= end_filter
        
        response = self.client.get(self.list_url, {'start_date': start_filter, 'end_date': end_filter})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.instance3_ag2_firing.pk)

    def test_list_history_filter_combination(self):
        """Test combination of status and fingerprint filters."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url, {'fingerprint': self.ag1.fingerprint, 'status': 'resolved'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.instance2_ag1_resolved.pk)
        
    def test_list_history_invalid_date_format(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url, {'start_date': 'invalid-date-format'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('start_date', response.data)
        self.assertIn('Enter a valid date/time.', str(response.data['start_date']))

    # --- Retrieve Action Tests (GET /history/{id}/) ---
    def test_retrieve_history_unauthenticated(self):
        """Test retrieving a single alert history instance by an unauthenticated user."""
        response = self.client.get(self.detail_url_i1)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_history_authenticated_exists(self):
        """Test retrieving an existing alert history instance by an authenticated user."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.detail_url_i1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.instance1_ag1_firing.id)
        self.assertEqual(response.data['status'], self.instance1_ag1_firing.status)
        self.assertEqual(response.data['alert_group_fingerprint'], self.instance1_ag1_firing.alert_group.fingerprint)
        self.assertEqual(response.data['annotations']['summary'], self.instance1_ag1_firing.annotations['summary'])
        # Verify 'ended_at' is present, even if None for firing alerts
        self.assertIn('ended_at', response.data) 
        if self.instance1_ag1_firing.ended_at:
            self.assertEqual(response.data['ended_at'], self.instance1_ag1_firing.ended_at.isoformat().replace('+00:00', 'Z'))
        else:
            self.assertIsNone(response.data['ended_at'])

    def test_retrieve_history_authenticated_resolved_instance_has_ended_at(self):
        """Test retrieving a resolved alert history instance includes ended_at."""
        self.client.force_authenticate(user=self.user)
        detail_url_i2 = reverse('alerts_api:alerthistory-detail', kwargs={'pk': self.instance2_ag1_resolved.pk})
        response = self.client.get(detail_url_i2)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.instance2_ag1_resolved.id)
        self.assertIsNotNone(response.data['ended_at'])
        self.assertEqual(response.data['ended_at'], self.instance2_ag1_resolved.ended_at.isoformat().replace('+00:00', 'Z'))


    def test_retrieve_history_authenticated_does_not_exist(self):
        """Test retrieving a non-existent alert history instance by an authenticated user."""
        self.client.force_authenticate(user=self.user)
        non_existent_detail_url = reverse('alerts_api:alerthistory-detail', kwargs={'pk': 99999}) # Non-existent PK
        response = self.client.get(non_existent_detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from alerts.models import AlertGroup, AlertInstance, AlertComment # Assuming models are in 'alerts' app
# from alerts.api.serializers import AlertGroupSerializer, AlertInstanceSerializer, AlertCommentSerializer # Will be used by the viewset

class AlertGroupViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testapiuser', password='password123', email='test@example.com')
        self.other_user = User.objects.create_user(username='otherapiuser', password='password456')

        # URLs
        self.list_url = reverse('alerts_api:alertgroup-list') # Default DRF naming

        # Create some AlertGroup instances
        self.ag1_firing_critical_unacked = AlertGroup.objects.create(
            fingerprint='fp1', name='High CPU Usage', severity='critical', current_status='firing',
            labels={'job': 'node_exporter', 'instance': 'server1', 'service': 'compute', 'cluster': 'prod-cl1', 'namespace': 'kube-system'},
            generator_url='http://prometheus.example.com/g0',
            description='CPU usage is high.', summary='High CPU on server1',
            first_seen=timezone.now() - timedelta(hours=5), last_seen=timezone.now() - timedelta(minutes=5),
            acknowledged=False, is_silenced=False, instance='server1', service='compute'
        )
        self.detail_url_ag1 = reverse('alerts_api:alertgroup-detail', kwargs={'fingerprint': self.ag1_firing_critical_unacked.fingerprint})
        self.acknowledge_url_ag1 = reverse('alerts_api:alertgroup-acknowledge', kwargs={'fingerprint': self.ag1_firing_critical_unacked.fingerprint})
        self.history_url_ag1 = reverse('alerts_api:alertgroup-history', kwargs={'fingerprint': self.ag1_firing_critical_unacked.fingerprint})
        self.comments_url_ag1 = reverse('alerts_api:alertgroup-comments', kwargs={'fingerprint': self.ag1_firing_critical_unacked.fingerprint})


        self.ag2_resolved_warning_acked = AlertGroup.objects.create(
            fingerprint='fp2', name='Disk Space Low', severity='warning', current_status='resolved',
            labels={'job': 'host_metrics', 'instance': 'server2', 'service': 'storage', 'cluster': 'staging-cl1', 'namespace': 'default'},
            generator_url='http://prometheus.example.com/g1',
            description='Disk space is low on server2.', summary='Low Disk on server2',
            first_seen=timezone.now() - timedelta(days=2), last_seen=timezone.now() - timedelta(hours=1),
            acknowledged=True, acknowledged_by=self.user, acknowledgement_time=timezone.now() - timedelta(hours=2),
            is_silenced=False, instance='server2', service='storage'
        )

        self.ag3_firing_info_silenced = AlertGroup.objects.create(
            fingerprint='fp3', name='Informational Event', severity='info', current_status='firing',
            labels={'job': 'kubernetes_events', 'instance': 'kube-apiserver', 'service': 'kube-system', 'cluster': 'dev-cl1', 'namespace': 'kube-system'},
            generator_url='http://prometheus.example.com/g2',
            description='An informational event occurred.', summary='Info event on dev cluster',
            first_seen=timezone.now() - timedelta(minutes=30), last_seen=timezone.now() - timedelta(minutes=1),
            acknowledged=False, is_silenced=True, instance='kube-apiserver', service='kube-system'
        )
        
        self.ag4_active_firing_critical_unacked_other_job = AlertGroup.objects.create(
            fingerprint='fp4', name='High Memory Usage', severity='critical', current_status='firing',
            labels={'job': 'another_exporter', 'instance': 'server3', 'service': 'memory_cache', 'cluster': 'prod-cl1', 'namespace': 'custom-ns'},
            generator_url='http://prometheus.example.com/g3',
            description='Memory usage is high on server3.', summary='High Memory on server3',
            first_seen=timezone.now() - timedelta(hours=2), last_seen=timezone.now() - timedelta(minutes=10),
            acknowledged=False, is_silenced=False, instance='server3', service='memory_cache'
        )

        # Create AlertInstance for history
        self.instance1_ag1 = AlertInstance.objects.create(
            alert_group=self.ag1_firing_critical_unacked, status='firing', 
            started_at=self.ag1_firing_critical_unacked.first_seen, 
            annotations={'summary': 'CPU spike detected on server1'}
        )
        self.instance2_ag1 = AlertInstance.objects.create(
            alert_group=self.ag1_firing_critical_unacked, status='resolved', 
            started_at=self.ag1_firing_critical_unacked.first_seen + timedelta(hours=1), 
            ended_at=self.ag1_firing_critical_unacked.first_seen + timedelta(hours=2),
            annotations={'summary': 'CPU spike resolved on server1'}
        )
        
        # Create AlertComment for comments
        self.comment1_ag1 = AlertComment.objects.create(
            alert_group=self.ag1_firing_critical_unacked, user=self.user, content="Investigating this CPU issue."
        )
        self.comment2_ag1 = AlertComment.objects.create(
            alert_group=self.ag1_firing_critical_unacked, user=self.other_user, content="Found the root cause."
        )

    # --- List Action Tests (GET /alerts/) ---
    def test_list_alerts_unauthenticated(self):
        """Test listing alerts by an unauthenticated user."""
        response = self.client.get(self.list_url)
        # Default for ReadOnlyModelViewSet is IsAuthenticatedOrReadOnly, but let's assume it's IsAuthenticated for now.
        # If it were IsAuthenticatedOrReadOnly, this would be 200.
        # Based on typical secure API design, list views often require auth.
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED) # Or HTTP_403_FORBIDDEN if using TokenAuth and no token

    def test_list_alerts_authenticated_default_active_only(self):
        """Test listing alerts by an authenticated user (default: active_only=true)."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # ag1 (firing), ag3 (firing, silenced), ag4 (firing) are active. ag2 is resolved.
        self.assertEqual(response.data['count'], 3) 
        fingerprints_in_response = [item['fingerprint'] for item in response.data['results']]
        self.assertIn(self.ag1_firing_critical_unacked.fingerprint, fingerprints_in_response)
        self.assertIn(self.ag3_firing_info_silenced.fingerprint, fingerprints_in_response)
        self.assertIn(self.ag4_active_firing_critical_unacked_other_job.fingerprint, fingerprints_in_response)
        self.assertNotIn(self.ag2_resolved_warning_acked.fingerprint, fingerprints_in_response) # Resolved

    def test_list_alerts_authenticated_active_only_false(self):
        """Test listing alerts with active_only=false."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url, {'active_only': 'false'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 4) # All alerts
        fingerprints_in_response = [item['fingerprint'] for item in response.data['results']]
        self.assertIn(self.ag1_firing_critical_unacked.fingerprint, fingerprints_in_response)
        self.assertIn(self.ag2_resolved_warning_acked.fingerprint, fingerprints_in_response)
        self.assertIn(self.ag3_firing_info_silenced.fingerprint, fingerprints_in_response)
        self.assertIn(self.ag4_active_firing_critical_unacked_other_job.fingerprint, fingerprints_in_response)

    def test_list_alerts_filter_by_severity(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url, {'severity': 'critical', 'active_only': 'false'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        fingerprints = [item['fingerprint'] for item in response.data['results']]
        self.assertIn(self.ag1_firing_critical_unacked.fingerprint, fingerprints)
        self.assertIn(self.ag4_active_firing_critical_unacked_other_job.fingerprint, fingerprints)

    def test_list_alerts_filter_by_current_status(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url, {'current_status': 'resolved', 'active_only': 'false'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['fingerprint'], self.ag2_resolved_warning_acked.fingerprint)

    def test_list_alerts_filter_by_acknowledged(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url, {'acknowledged': 'true', 'active_only': 'false'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['fingerprint'], self.ag2_resolved_warning_acked.fingerprint)

    def test_list_alerts_filter_by_instance(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url, {'instance': 'server1', 'active_only': 'false'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['fingerprint'], self.ag1_firing_critical_unacked.fingerprint)

    def test_list_alerts_filter_by_service(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url, {'service': 'compute', 'active_only': 'false'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['fingerprint'], self.ag1_firing_critical_unacked.fingerprint)

    def test_list_alerts_filter_by_job(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url, {'job': 'node_exporter', 'active_only': 'false'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['fingerprint'], self.ag1_firing_critical_unacked.fingerprint)
        
    def test_list_alerts_filter_by_cluster(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url, {'cluster': 'prod-cl1', 'active_only': 'false'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2) # ag1 and ag4
        fingerprints = [item['fingerprint'] for item in response.data['results']]
        self.assertIn(self.ag1_firing_critical_unacked.fingerprint, fingerprints)
        self.assertIn(self.ag4_active_firing_critical_unacked_other_job.fingerprint, fingerprints)

    def test_list_alerts_filter_by_namespace(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url, {'namespace': 'kube-system', 'active_only': 'false'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2) # ag1 and ag3
        fingerprints = [item['fingerprint'] for item in response.data['results']]
        self.assertIn(self.ag1_firing_critical_unacked.fingerprint, fingerprints)
        self.assertIn(self.ag3_firing_info_silenced.fingerprint, fingerprints)

    def test_list_alerts_search_by_name(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url, {'search': 'High CPU Usage', 'active_only': 'false'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['fingerprint'], self.ag1_firing_critical_unacked.fingerprint)

    def test_list_alerts_search_by_fingerprint(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url, {'search': 'fp2', 'active_only': 'false'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['fingerprint'], self.ag2_resolved_warning_acked.fingerprint)

    def test_list_alerts_search_by_instance_partial(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url, {'search': 'server', 'active_only': 'false'}) # Matches server1, server2, server3
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)

    def test_list_alerts_search_by_service(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url, {'search': 'storage', 'active_only': 'false'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['fingerprint'], self.ag2_resolved_warning_acked.fingerprint)

    def test_list_alerts_pagination_structure(self):
        """Test basic pagination structure."""
        self.client.force_authenticate(user=self.user)
        # Create more than default page size (assuming it's around 10-20)
        for i in range(25):
            AlertGroup.objects.create(
                fingerprint=f'pagefp{i}', name=f'Page Test Alert {i}', severity='info', current_status='firing',
                labels={'job': 'pagination_test'}, instance=f'pageserver{i}'
            )
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('results', response.data)
        self.assertTrue(isinstance(response.data['results'], list))
        # Count will include the 4 from setUp + 25 new ones that are firing
        self.assertEqual(response.data['count'], 3 + 25) 
        self.assertIsNotNone(response.data['next']) # Expecting a next page

    # --- Retrieve Action Tests (GET /alerts/{fingerprint}/) ---
    def test_retrieve_alert_unauthenticated(self):
        """Test retrieving a single alert by an unauthenticated user."""
        response = self.client.get(self.detail_url_ag1)
        # IsAuthenticatedOrReadOnly would allow this, but if default is IsAuthenticated:
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_alert_authenticated_exists(self):
        """Test retrieving an existing alert by an authenticated user."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.detail_url_ag1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['fingerprint'], self.ag1_firing_critical_unacked.fingerprint)
        self.assertEqual(response.data['name'], self.ag1_firing_critical_unacked.name)
        self.assertEqual(response.data['severity'], self.ag1_firing_critical_unacked.severity)
        # Check a few key fields from the serializer
        self.assertIn('labels', response.data)
        self.assertEqual(response.data['labels'], self.ag1_firing_critical_unacked.labels)
        self.assertIn('acknowledged_by_username', response.data)
        self.assertIn('last_seen_display', response.data)

    def test_retrieve_alert_authenticated_does_not_exist(self):
        """Test retrieving a non-existent alert by an authenticated user."""
        self.client.force_authenticate(user=self.user)
        non_existent_detail_url = reverse('alerts_api:alertgroup-detail', kwargs={'fingerprint': 'nonexistentfp'})
        response = self.client.get(non_existent_detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- Acknowledge Action Tests (PUT /alerts/{fingerprint}/acknowledge/) ---
    @patch('alerts.services.alerts_processor.acknowledge_alert') # Patch where it's imported in the service layer if used by view, or in view itself
    def test_acknowledge_alert_success(self, mock_acknowledge_alert_service):
        """Test successfully acknowledging an unacknowledged alert."""
        self.client.force_authenticate(user=self.user)
        fingerprint = self.ag1_firing_critical_unacked.fingerprint
        comment_text = "Acknowledging this via API."

        # Mock the service function to avoid actual DB changes by it, focus on view logic
        # The service is expected to return the updated alert_group
        mock_updated_alert_group = AlertGroup.objects.get(fingerprint=fingerprint)
        mock_updated_alert_group.acknowledged = True
        mock_updated_alert_group.acknowledged_by = self.user
        mock_updated_alert_group.acknowledgement_time = timezone.now()
        mock_acknowledge_alert_service.return_value = mock_updated_alert_group

        response = self.client.put(
            self.acknowledge_url_ag1,
            {'acknowledged': True, 'comment': comment_text},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(response.data['message'], f"Alert '{self.ag1_firing_critical_unacked.name}' acknowledged.")

        mock_acknowledge_alert_service.assert_called_once()
        args, kwargs = mock_acknowledge_alert_service.call_args
        self.assertEqual(kwargs['alert_group'].fingerprint, fingerprint)
        self.assertEqual(kwargs['user'], self.user)
        self.assertEqual(kwargs['comment'], comment_text)
        
        # Check if an AlertComment was created (this is usually done by the service or signal)
        # For this test, we'll assume the view or a signal connected to the service call handles comment creation.
        # If acknowledge_alert service itself creates the comment, then this check is valid.
        # As per the current setup, the view calls the service, then creates a comment.
        self.assertTrue(AlertComment.objects.filter(
            alert_group=self.ag1_firing_critical_unacked, 
            user=self.user, 
            content=f"Alert Acknowledged: {comment_text}" # Default prefix
        ).exists())

    @patch('alerts.services.alerts_processor.unacknowledge_alert') # Assuming a similar service for un-ack
    def test_unacknowledge_alert_success(self, mock_unacknowledge_alert_service):
        """Test successfully un-acknowledging an acknowledged alert."""
        self.client.force_authenticate(user=self.user)
        fingerprint = self.ag2_resolved_warning_acked.fingerprint # This one is acked
        comment_text = "Un-acknowledging this via API."

        mock_updated_alert_group = AlertGroup.objects.get(fingerprint=fingerprint)
        mock_updated_alert_group.acknowledged = False
        mock_updated_alert_group.acknowledged_by = None
        mock_updated_alert_group.acknowledgement_time = None
        mock_unacknowledge_alert_service.return_value = mock_updated_alert_group
        
        response = self.client.put(
            reverse('alerts_api:alertgroup-acknowledge', kwargs={'fingerprint': fingerprint}),
            {'acknowledged': False, 'comment': comment_text},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(response.data['message'], f"Alert '{self.ag2_resolved_warning_acked.name}' un-acknowledged.")

        mock_unacknowledge_alert_service.assert_called_once()
        args, kwargs = mock_unacknowledge_alert_service.call_args
        self.assertEqual(kwargs['alert_group'].fingerprint, fingerprint)
        self.assertEqual(kwargs['user'], self.user) # User performing the action
        self.assertEqual(kwargs['comment'], comment_text)
        
        self.assertTrue(AlertComment.objects.filter(
            alert_group=self.ag2_resolved_warning_acked, 
            user=self.user, 
            content=f"Alert Un-acknowledged: {comment_text}"
        ).exists())

    def test_acknowledge_alert_missing_comment(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.put(
            self.acknowledge_url_ag1,
            {'acknowledged': True}, # Missing comment
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('comment', response.data)
        self.assertIn('This field is required.', str(response.data['comment']))

    def test_acknowledge_alert_missing_acknowledged_field(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.put(
            self.acknowledge_url_ag1,
            {'comment': 'A comment'}, # Missing 'acknowledged' field
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('acknowledged', response.data)
        self.assertIn('This field is required.', str(response.data['acknowledged']))

    def test_acknowledge_alert_non_boolean_acknowledged(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.put(
            self.acknowledge_url_ag1,
            {'acknowledged': 'not-a-boolean', 'comment': 'A comment'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('acknowledged', response.data)
        self.assertIn('Must be a valid boolean.', str(response.data['acknowledged']))

    def test_acknowledge_alert_non_existent(self):
        self.client.force_authenticate(user=self.user)
        non_existent_ack_url = reverse('alerts_api:alertgroup-acknowledge', kwargs={'fingerprint': 'nonexistentfp'})
        response = self.client.put(
            non_existent_ack_url,
            {'acknowledged': True, 'comment': 'Trying to ack non-existent'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_acknowledge_alert_unauthenticated(self):
        response = self.client.put(
            self.acknowledge_url_ag1,
            {'acknowledged': True, 'comment': 'Unauth attempt'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- History Action Tests (GET /alerts/{fingerprint}/history/) ---
    def test_history_alert_unauthenticated(self):
        """Test getting history for an alert by an unauthenticated user."""
        response = self.client.get(self.history_url_ag1)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_history_alert_authenticated_exists(self):
        """Test getting history for an existing alert by an authenticated user."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.history_url_ag1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(isinstance(response.data, list)) # Should be a list of instances
        self.assertEqual(len(response.data), 2) # instance1_ag1 and instance2_ag1
        
        # Check some data from the first instance (newest first by default ordering in serializer/view)
        # Assuming AlertInstanceSerializer serializes 'status' and 'started_at'
        # And that the default ordering is -started_at
        fingerprints_in_response = [item['alert_group_fingerprint'] for item in response.data]
        self.assertIn(self.ag1_firing_critical_unacked.fingerprint, fingerprints_in_response[0])
        self.assertIn(self.ag1_firing_critical_unacked.fingerprint, fingerprints_in_response[1])

        # More specific checks if serializer details are known
        # Example: check for specific annotations or timestamps
        first_instance_data = response.data[0] # Assuming default ordering by -started_at (newest first)
        second_instance_data = response.data[1]

        # The order depends on the ViewSet's ordering. Let's find them by a unique property if possible.
        # Or ensure the order is predictable. If ordered by '-started_at':
        if first_instance_data['started_at'] > second_instance_data['started_at']:
            newest_instance_in_response = first_instance_data
            older_instance_in_response = second_instance_data
        else:
            newest_instance_in_response = second_instance_data
            older_instance_in_response = first_instance_data

        self.assertEqual(newest_instance_in_response['status'], self.instance2_ag1.status) # resolved (more recent ended_at)
        self.assertEqual(older_instance_in_response['status'], self.instance1_ag1.status) # firing
        self.assertEqual(newest_instance_in_response['annotations']['summary'], self.instance2_ag1.annotations['summary'])
        self.assertEqual(older_instance_in_response['annotations']['summary'], self.instance1_ag1.annotations['summary'])


    def test_history_alert_authenticated_no_history(self):
        """Test getting history for an alert with no instances by an authenticated user."""
        self.client.force_authenticate(user=self.user)
        # ag2 has no instances created in setUp
        history_url_ag2 = reverse('alerts_api:alertgroup-history', kwargs={'fingerprint': self.ag2_resolved_warning_acked.fingerprint})
        response = self.client.get(history_url_ag2)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(isinstance(response.data, list))
        self.assertEqual(len(response.data), 0)

    def test_history_alert_authenticated_does_not_exist(self):
        """Test getting history for a non-existent alert by an authenticated user."""
        self.client.force_authenticate(user=self.user)
        non_existent_history_url = reverse('alerts_api:alertgroup-history', kwargs={'fingerprint': 'nonexistentfp'})
        response = self.client.get(non_existent_history_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- Comments Action Tests (GET & POST /alerts/{fingerprint}/comments/) ---
    def test_get_comments_unauthenticated(self):
        """Test getting comments for an alert by an unauthenticated user."""
        response = self.client.get(self.comments_url_ag1)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_comments_authenticated_exists(self):
        """Test getting comments for an existing alert by an authenticated user."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.comments_url_ag1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(isinstance(response.data, list))
        self.assertEqual(len(response.data), 2) # comment1_ag1 and comment2_ag1
        
        # Check some data from the comments, assuming AlertCommentSerializer serializes 'user_username' and 'content'
        # Order might depend on the viewset's ordering for comments.
        # Let's assume newest first by 'created_at' (descending)
        comment_contents = [item['content'] for item in response.data]
        self.assertIn(self.comment1_ag1.content, comment_contents)
        self.assertIn(self.comment2_ag1.content, comment_contents)
        
        # Example: check user of the first comment if order is predictable
        # (Assuming default ordering is by 'created_at' ascending)
        self.assertEqual(response.data[0]['user_username'], self.user.username)
        self.assertEqual(response.data[1]['user_username'], self.other_user.username)


    def test_get_comments_authenticated_no_comments(self):
        """Test getting comments for an alert with no comments by an authenticated user."""
        self.client.force_authenticate(user=self.user)
        comments_url_ag2 = reverse('alerts_api:alertgroup-comments', kwargs={'fingerprint': self.ag2_resolved_warning_acked.fingerprint})
        response = self.client.get(comments_url_ag2)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(isinstance(response.data, list))
        self.assertEqual(len(response.data), 0)

    def test_get_comments_authenticated_alert_does_not_exist(self):
        """Test getting comments for a non-existent alert by an authenticated user."""
        self.client.force_authenticate(user=self.user)
        non_existent_comments_url = reverse('alerts_api:alertgroup-comments', kwargs={'fingerprint': 'nonexistentfp'})
        response = self.client.get(non_existent_comments_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_comment_unauthenticated(self):
        """Test posting a comment by an unauthenticated user."""
        response = self.client.post(self.comments_url_ag1, {'content': 'Unauth comment'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_post_comment_authenticated_valid_data(self):
        """Test posting a valid comment by an authenticated user."""
        self.client.force_authenticate(user=self.user)
        comment_content = "This is a new API comment."
        response = self.client.post(self.comments_url_ag1, {'content': comment_content}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], comment_content)
        self.assertEqual(response.data['user_username'], self.user.username)
        self.assertEqual(response.data['alert_group_fingerprint'], self.ag1_firing_critical_unacked.fingerprint)
        
        # Verify the comment was actually created in the DB
        self.assertTrue(AlertComment.objects.filter(
            alert_group=self.ag1_firing_critical_unacked,
            user=self.user,
            content=comment_content
        ).exists())

    def test_post_comment_authenticated_invalid_data_empty(self):
        """Test posting an empty comment by an authenticated user."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.comments_url_ag1, {'content': ''}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('content', response.data)
        self.assertIn('This field may not be blank.', str(response.data['content']))

    def test_post_comment_authenticated_invalid_data_missing_content(self):
        """Test posting with missing 'content' field by an authenticated user."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.comments_url_ag1, {}, format='json') # Empty data
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('content', response.data)
        self.assertIn('This field is required.', str(response.data['content']))

    def test_post_comment_authenticated_alert_does_not_exist(self):
        """Test posting a comment to a non-existent alert by an authenticated user."""
        self.client.force_authenticate(user=self.user)
        non_existent_comments_url = reverse('alerts_api:alertgroup-comments', kwargs={'fingerprint': 'nonexistentfp'})
        response = self.client.post(non_existent_comments_url, {'content': 'Comment to non-existent alert'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('alerts.tasks.process_alert_payload_task.delay')
    def test_post_valid_payload(self, mock_process_task):
        """
        Test POST with a valid Alertmanager payload.
        """
        response = self.client.post(self.webhook_url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'status': 'success (task queued)'})
        
        # Verify the task was called with the exact payload received
        mock_process_task.assert_called_once_with(self.valid_payload)

    @patch('alerts.tasks.process_alert_payload_task.delay')
    def test_post_valid_payload_multiple_alerts(self, mock_process_task):
        """
        Test POST with a valid payload containing multiple alerts.
        """
        payload_multiple_alerts = self.valid_payload.copy()
        payload_multiple_alerts['alerts'].append({
            "status": "firing",
            "labels": {"alertname": "AnotherAlert", "instance": "server2", "severity": "warning"},
            "annotations": {"summary": "Another alert firing"},
            "startsAt": "2023-10-26T11:00:00Z",
            "endsAt": "0001-01-01T00:00:00Z",
            "generatorURL": "http://prometheus.example.com/graph?g0.expr=...",
            "fingerprint": "fingerprint456"
        })
        
        response = self.client.post(self.webhook_url, payload_multiple_alerts, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'status': 'success (task queued)'})
        mock_process_task.assert_called_once_with(payload_multiple_alerts)

    # No authentication required due to permission_classes = [AllowAny]
    # So no specific test for unauthenticated access is needed beyond what's covered.

    @patch('alerts.tasks.process_alert_payload_task.delay')
    def test_post_invalid_payload_missing_required_field(self, mock_process_task):
        """
        Test POST with a payload missing a required field (e.g., 'alerts' list).
        """
        response = self.client.post(self.webhook_url, self.invalid_payload_missing_alerts, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('alerts', response.data) # Serializer should report 'alerts' as a required field
        self.assertIn('This field is required.', str(response.data['alerts']))
        mock_process_task.assert_not_called()

    @patch('alerts.tasks.process_alert_payload_task.delay')
    def test_post_invalid_payload_bad_alert_item_structure(self, mock_process_task):
        """
        Test POST with a payload where an item in the 'alerts' list has an invalid structure.
        """
        response = self.client.post(self.webhook_url, self.invalid_payload_bad_alert_structure, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Example: {"alerts": [{"labels": ["This field is required."]}]}
        self.assertIn('alerts', response.data)
        self.assertTrue(isinstance(response.data['alerts'], list))
        self.assertTrue(isinstance(response.data['alerts'][0], dict))
        self.assertIn('labels', response.data['alerts'][0])
        self.assertIn('This field is required.', str(response.data['alerts'][0]['labels']))
        mock_process_task.assert_not_called()

    @patch('alerts.tasks.process_alert_payload_task.delay')
    def test_post_empty_payload(self, mock_process_task):
        """
        Test POST with an empty JSON object.
        """
        response = self.client.post(self.webhook_url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Expect errors for all required fields of AlertmanagerWebhookSerializer
        self.assertIn('version', response.data)
        self.assertIn('status', response.data)
        self.assertIn('alerts', response.data)
        mock_process_task.assert_not_called()

    @patch('alerts.tasks.process_alert_payload_task.delay')
    @patch('alerts.api.views.AlertmanagerWebhookSerializer') # Mock the serializer to control its output
    def test_post_task_serialization_error(self, mock_serializer_class, mock_process_task):
        """
        Test POST where the serializer is valid, but an issue occurs before task queuing
        (e.g., if the validated data from serializer was somehow not directly usable by the task or
        if there was an unexpected error before .delay() call related to data handling).
        For this specific view, the most direct way to simulate an issue before .delay() if data is valid,
        is to have .delay() itself raise an error, or mock an intermediate step if one existed.
        Given the current view structure, if serializer.is_valid() is true, data is passed to .delay().
        Let's simulate an error during the .delay() call itself, perhaps due to Celery configuration issue
        or an unexpected problem with the data that Celery's pickling can't handle.
        """
        # Make the serializer valid
        mock_serializer_instance = mock_serializer_class.return_value
        mock_serializer_instance.is_valid.return_value = True
        mock_serializer_instance.validated_data = self.valid_payload # Use valid data for the task

        # Make the .delay() call raise an exception (e.g., CeleryNotInstalledError or a pickling error)
        mock_process_task.side_effect = Exception("Celery task queuing failed")

        response = self.client.post(self.webhook_url, self.valid_payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('error', response.data)
        self.assertIn('Failed to queue alert processing task', response.data['error'])
        
        mock_process_task.assert_called_once_with(self.valid_payload)

    def test_get_not_allowed(self):
        response = self.client.get(self.webhook_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_put_not_allowed(self):
        response = self.client.put(self.webhook_url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_not_allowed(self):
        response = self.client.delete(self.webhook_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_patch_not_allowed(self):
        response = self.client.patch(self.webhook_url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        self.invalid_payload_missing_alerts = {
            "version": "4",
            "groupKey": "{}:{alertname=\"HighCPUUsage\"}",
            "status": "firing",
            "receiver": "webhook-receiver",
            # Missing 'alerts' key
        }
        
        self.invalid_payload_bad_alert_structure = {
            "version": "4",
            "groupKey": "{}:{alertname=\"HighCPUUsage\"}",
            "status": "firing",
            "receiver": "webhook-receiver",
            "alerts": [
                {
                    "status": "firing",
                    # Missing 'labels'
                    "annotations": {"summary": "Incomplete alert"}
                }
            ]
        }
