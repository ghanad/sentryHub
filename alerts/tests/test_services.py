# alerts/tests/test_services.py

import unittest
import datetime
import json
from django.test import TestCase, TransactionTestCase # Use TestCase for DB interactions
from django.contrib.auth.models import User
from django.utils import timezone
from unittest.mock import patch
from dateutil.parser import parse as parse_datetime

# Import models and services from the parent 'alerts' app
from ..models import AlertGroup, AlertInstance, AlertAcknowledgementHistory
from ..services.alerts_processor import acknowledge_alert, get_active_firing_instance
from ..services.alert_state_manager import update_alert_state
from ..services.payload_parser import parse_alertmanager_payload

# --- Tests for alerts_processor.py ---

class AcknowledgeAlertTests(TransactionTestCase):
    # Keep existing tests for acknowledge_alert from test_forms.py if they were moved here
    # Or copy them from test_forms.py results if needed.
    # Example structure:
    def setUp(self):
        self.user = User.objects.create_user(username='ack_user', password='password')
        self.alert_group = AlertGroup.objects.create(
            name='Test Ack Alert',
            fingerprint='test-ack-fingerprint',
            current_status='firing',
            labels={'alertname': 'TestAckAlert'},
            severity='warning'
        )

    def test_acknowledge_alert_basic(self):
        comment = "Acknowledging this."
        acknowledge_alert(self.alert_group, self.user, comment)
        self.alert_group.refresh_from_db()
        self.assertTrue(self.alert_group.acknowledged)
        self.assertEqual(self.alert_group.acknowledged_by, self.user)
        self.assertIsNotNone(self.alert_group.acknowledgement_time)
        history_exists = AlertAcknowledgementHistory.objects.filter(
            alert_group=self.alert_group,
            acknowledged_by=self.user,
            comment=comment
        ).exists()
        self.assertTrue(history_exists)

    # Add more tests for acknowledge_alert based on test_forms.py results

class GetActiveFiringInstanceTests(TestCase):
    # Keep existing tests for get_active_firing_instance from test_forms.py if they were moved here
    # Or copy them from test_forms.py results if needed.
    # Example structure:
    def setUp(self):
        self.alert_group_active = AlertGroup.objects.create(fingerprint="fg_active", name="Active Group", labels={})
        self.active_instance = AlertInstance.objects.create(
            alert_group=self.alert_group_active, status='firing', started_at=timezone.now() - datetime.timedelta(minutes=5), ended_at=None, annotations={}
        )
        self.resolved_instance = AlertInstance.objects.create(
            alert_group=self.alert_group_active, status='resolved', started_at=timezone.now() - datetime.timedelta(minutes=10), ended_at=timezone.now() - datetime.timedelta(minutes=8), annotations={}
        )
        self.alert_group_resolved = AlertGroup.objects.create(fingerprint="fg_resolved", name="Resolved Group", labels={})
        AlertInstance.objects.create(
            alert_group=self.alert_group_resolved, status='resolved', started_at=timezone.now() - datetime.timedelta(minutes=15), ended_at=timezone.now() - datetime.timedelta(minutes=12), annotations={}
        )

    def test_get_active_instance_present(self):
        instance = get_active_firing_instance(self.alert_group_active)
        self.assertEqual(instance, self.active_instance)

    def test_get_active_instance_absent(self):
        instance = get_active_firing_instance(self.alert_group_resolved)
        self.assertIsNone(instance)

    # Add more tests for get_active_firing_instance based on test_forms.py results


# --- Tests for alert_state_manager.py ---

class UpdateAlertStateTests(TestCase):

    def test_new_firing_alert_creates_group_and_instance(self):
        """Scenario 1: New 'firing' alert creates AlertGroup and AlertInstance."""
        start_time = timezone.now() - datetime.timedelta(minutes=1)
        parsed_data = {
            'fingerprint': 'new-fg-1',
            'status': 'firing',
            'labels': {'alertname': 'NewAlert', 'severity': 'critical', 'instance': 'host1'},
            'starts_at': start_time,
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
        self.assertDictEqual(created_group.labels, parsed_data['labels'])
        self.assertAlmostEqual(created_group.first_occurrence, timezone.now(), delta=datetime.timedelta(seconds=5))
        self.assertAlmostEqual(created_group.last_occurrence, timezone.now(), delta=datetime.timedelta(seconds=5))

        created_instance = AlertInstance.objects.get(alert_group=created_group)
        self.assertEqual(created_instance.status, 'firing')
        self.assertEqual(created_instance.started_at, start_time)
        self.assertIsNone(created_instance.ended_at)
        self.assertDictEqual(created_instance.annotations, parsed_data['annotations'])
        self.assertEqual(created_instance.generator_url, parsed_data['generator_url'])
        self.assertIsNone(created_instance.resolution_type)

    def test_new_firing_for_existing_resolved_group(self):
        """Scenario 2: New 'firing' alert for an existing resolved group."""
        initial_time = timezone.now() - datetime.timedelta(days=1)
        existing_group = AlertGroup.objects.create(
            fingerprint='existing-resolved-fg', name='Resolved Alert', labels={'app': 'test'},
            current_status='resolved', total_firing_count=2, last_occurrence=initial_time
        )
        start_time = timezone.now() - datetime.timedelta(minutes=5)
        parsed_data = {
            'fingerprint': 'existing-resolved-fg', 'status': 'firing', 'labels': {'app': 'test'},
            'starts_at': start_time, 'ends_at': None, 'annotations': {'summary': 'Firing again'},
            'generator_url': ''
        }

        alert_group, alert_instance = update_alert_state(parsed_data)

        self.assertEqual(alert_group.pk, existing_group.pk)
        alert_group.refresh_from_db()
        self.assertEqual(alert_group.current_status, 'firing')
        self.assertEqual(alert_group.total_firing_count, 3) # Incremented
        self.assertAlmostEqual(alert_group.last_occurrence, timezone.now(), delta=datetime.timedelta(seconds=5))

        self.assertIsNotNone(alert_instance)
        self.assertEqual(alert_instance.alert_group, alert_group)
        self.assertEqual(alert_instance.status, 'firing')
        self.assertEqual(alert_instance.started_at, start_time)
        self.assertIsNone(alert_instance.ended_at)

    def test_re_fire_existing_firing_group(self):
        """Scenario 3: New 'firing' alert for existing firing group (Re-fire)."""
        initial_start = timezone.now() - datetime.timedelta(hours=1)
        existing_group = AlertGroup.objects.create(
            fingerprint='re-fire-fg', name='Refire Alert', labels={'job': 'worker'},
            current_status='firing', total_firing_count=1
        )
        initial_instance = AlertInstance.objects.create(
            alert_group=existing_group, status='firing', started_at=initial_start,
            ended_at=None, annotations={'summary': 'Initial fire'}
        )
        new_start = timezone.now() - datetime.timedelta(minutes=2)
        parsed_data = {
            'fingerprint': 're-fire-fg', 'status': 'firing', 'labels': {'job': 'worker'},
            'starts_at': new_start, 'ends_at': None, 'annotations': {'summary': 'Second fire'},
            'generator_url': ''
        }

        alert_group, new_instance = update_alert_state(parsed_data)

        self.assertEqual(alert_group.pk, existing_group.pk)
        alert_group.refresh_from_db()
        self.assertEqual(alert_group.current_status, 'firing')
        # NOTE: Based on current logic, total_firing_count does NOT increment on fire -> fire
        self.assertEqual(alert_group.total_firing_count, 1)
        self.assertAlmostEqual(alert_group.last_occurrence, timezone.now(), delta=datetime.timedelta(seconds=5))

        # Check previous instance was marked resolved (inferred)
        initial_instance.refresh_from_db()
        self.assertEqual(initial_instance.status, 'resolved')
        self.assertIsNone(initial_instance.ended_at) # ended_at should remain None
        self.assertEqual(initial_instance.resolution_type, 'inferred')

        # Check new instance
        self.assertIsNotNone(new_instance)
        self.assertEqual(new_instance.alert_group, alert_group)
        self.assertEqual(new_instance.status, 'firing')
        self.assertEqual(new_instance.started_at, new_start)
        self.assertIsNone(new_instance.ended_at)

    def test_resolved_matches_existing_firing(self):
        """Scenario 4: 'resolved' alert matching an existing 'firing' instance."""
        start_time = timezone.now() - datetime.timedelta(minutes=30)
        end_time = timezone.now() - datetime.timedelta(minutes=1)
        existing_group = AlertGroup.objects.create(
            fingerprint='resolve-match-fg', name='Resolve Match', labels={'id': '123'},
            current_status='firing', total_firing_count=1
        )
        firing_instance = AlertInstance.objects.create(
            alert_group=existing_group, status='firing', started_at=start_time,
            ended_at=None, annotations={}
        )
        parsed_data = {
            'fingerprint': 'resolve-match-fg', 'status': 'resolved', 'labels': {'id': '123'},
            'starts_at': start_time, 'ends_at': end_time, 'annotations': {}, 'generator_url': ''
        }

        alert_group, resolved_instance = update_alert_state(parsed_data)

        self.assertEqual(alert_group.pk, existing_group.pk)
        alert_group.refresh_from_db()
        self.assertEqual(alert_group.current_status, 'resolved')
        self.assertAlmostEqual(alert_group.last_occurrence, timezone.now(), delta=datetime.timedelta(seconds=5))

        # Check the existing instance was updated
        self.assertEqual(resolved_instance.pk, firing_instance.pk)
        resolved_instance.refresh_from_db()
        self.assertEqual(resolved_instance.status, 'resolved')
        self.assertEqual(resolved_instance.started_at, start_time)
        self.assertEqual(resolved_instance.ended_at, end_time)
        self.assertEqual(resolved_instance.resolution_type, 'normal')
        self.assertEqual(AlertInstance.objects.filter(alert_group=alert_group).count(), 1) # No new instance

    def test_resolved_no_matching_firing(self):
        """Scenario 5: 'resolved' alert with no matching 'firing' instance."""
        start_time = timezone.now() - datetime.timedelta(minutes=45)
        end_time = timezone.now() - datetime.timedelta(minutes=5)
        existing_group = AlertGroup.objects.create(
            fingerprint='resolve-nomatch-fg', name='Resolve No Match', labels={'id': '456'},
            current_status='resolved', total_firing_count=1 # Group already resolved
        )
        # No firing instance exists for this start_time
        parsed_data = {
            'fingerprint': 'resolve-nomatch-fg', 'status': 'resolved', 'labels': {'id': '456'},
            'starts_at': start_time, 'ends_at': end_time, 'annotations': {}, 'generator_url': ''
        }

        alert_group, new_resolved_instance = update_alert_state(parsed_data)

        self.assertEqual(alert_group.pk, existing_group.pk)
        alert_group.refresh_from_db()
        self.assertEqual(alert_group.current_status, 'resolved') # Remains resolved
        self.assertAlmostEqual(alert_group.last_occurrence, timezone.now(), delta=datetime.timedelta(seconds=5))

        # Check a new resolved instance was created
        self.assertIsNotNone(new_resolved_instance)
        self.assertTrue(new_resolved_instance.pk is not None)
        self.assertEqual(new_resolved_instance.alert_group, alert_group)
        self.assertEqual(new_resolved_instance.status, 'resolved')
        self.assertEqual(new_resolved_instance.started_at, start_time)
        self.assertEqual(new_resolved_instance.ended_at, end_time)
        self.assertEqual(new_resolved_instance.resolution_type, 'normal')

    def test_resolved_idempotency(self):
        """Scenario 6: 'resolved' alert for already resolved group (Idempotency)."""
        start_time = timezone.now() - datetime.timedelta(hours=2)
        end_time = timezone.now() - datetime.timedelta(hours=1)
        existing_group = AlertGroup.objects.create(
            fingerprint='resolve-idem-fg', name='Resolve Idem', labels={'id': '789'},
            current_status='resolved', total_firing_count=1
        )
        AlertInstance.objects.create(
            alert_group=existing_group, status='resolved', started_at=start_time,
            ended_at=end_time, annotations={}, resolution_type='normal'
        )
        parsed_data = {
            'fingerprint': 'resolve-idem-fg', 'status': 'resolved', 'labels': {'id': '789'},
            'starts_at': start_time, 'ends_at': end_time, 'annotations': {}, 'generator_url': ''
        }

        initial_instance_count = AlertInstance.objects.filter(alert_group=existing_group).count()

        alert_group, instance = update_alert_state(parsed_data)

        self.assertEqual(alert_group.pk, existing_group.pk)
        alert_group.refresh_from_db()
        self.assertEqual(alert_group.current_status, 'resolved')
        self.assertAlmostEqual(alert_group.last_occurrence, timezone.now(), delta=datetime.timedelta(seconds=5))
        self.assertIsNone(instance) # Function should return None as no new instance created/updated
        self.assertEqual(AlertInstance.objects.filter(alert_group=existing_group).count(), initial_instance_count) # Count unchanged

    def test_missing_instance_label(self):
        """Scenario 7: Alert data missing 'instance' label."""
        start_time = timezone.now()
        parsed_data = {
            'fingerprint': 'no-instance-fg', 'status': 'firing',
            'labels': {'alertname': 'NoInstance', 'severity': 'info'}, # No 'instance' key
            'starts_at': start_time, 'ends_at': None, 'annotations': {}, 'generator_url': ''
        }
        alert_group, alert_instance = update_alert_state(parsed_data)
        self.assertIsNotNone(alert_group)
        self.assertIsNone(alert_group.instance)

    def test_missing_alertname_label(self):
        """Scenario 8: Alert data missing 'alertname' label."""
        start_time = timezone.now()
        parsed_data = {
            'fingerprint': 'no-name-fg', 'status': 'firing',
            'labels': {'severity': 'warning', 'instance': 'host2'}, # No 'alertname' key
            'starts_at': start_time, 'ends_at': None, 'annotations': {}, 'generator_url': ''
        }
        alert_group, alert_instance = update_alert_state(parsed_data)
        self.assertIsNotNone(alert_group)
        self.assertEqual(alert_group.name, 'Unknown Alert')
        self.assertEqual(alert_group.instance, 'host2')


    def test_duplicate_firing_event_skipped(self):
        """Scenario: Duplicate 'firing' alert is skipped."""
        start_time = timezone.now() - datetime.timedelta(minutes=10)
        existing_group = AlertGroup.objects.create(
            fingerprint='duplicate-fire-fg', name='Duplicate Fire', labels={},
            current_status='firing', total_firing_count=1
        )
        AlertInstance.objects.create(
            alert_group=existing_group, status='firing', started_at=start_time,
            ended_at=None, annotations={}
        )
        parsed_data = {
            'fingerprint': 'duplicate-fire-fg', 'status': 'firing', 'labels': {},
            'starts_at': start_time, 'ends_at': None, 'annotations': {}, 'generator_url': ''
        }

        initial_instance_count = AlertInstance.objects.filter(alert_group=existing_group).count()

        # Use patch to capture logger output
        with patch('alerts.services.alert_state_manager.logger.warning') as mock_warning:
            alert_group, alert_instance = update_alert_state(parsed_data)

        self.assertEqual(alert_group.pk, existing_group.pk)
        self.assertIsNone(alert_instance) # No new instance created
        self.assertEqual(AlertInstance.objects.filter(alert_group=existing_group).count(), initial_instance_count) # Count unchanged
        mock_warning.assert_called_once()
        self.assertIn("Duplicate firing event detected", mock_warning.call_args[0][0])

    def test_duplicate_resolved_event_skipped(self):
        """Scenario: Duplicate 'resolved' alert is skipped."""
        start_time = timezone.now() - datetime.timedelta(hours=2)
        end_time = timezone.now() - datetime.timedelta(hours=1)
        existing_group = AlertGroup.objects.create(
            fingerprint='duplicate-resolved-fg', name='Duplicate Resolved', labels={},
            current_status='resolved', total_firing_count=1
        )
        AlertInstance.objects.create(
            alert_group=existing_group, status='resolved', started_at=start_time,
            ended_at=end_time, annotations={}, resolution_type='normal'
        )
        parsed_data = {
            'fingerprint': 'duplicate-resolved-fg', 'status': 'resolved', 'labels': {},
            'starts_at': start_time, 'ends_at': end_time, 'annotations': {}, 'generator_url': ''
        }

        initial_instance_count = AlertInstance.objects.filter(alert_group=existing_group).count()

        with patch('alerts.services.alert_state_manager.logger.warning') as mock_warning:
            alert_group, alert_instance = update_alert_state(parsed_data)

        self.assertEqual(alert_group.pk, existing_group.pk)
        self.assertIsNone(alert_instance) # No new instance created/updated
        self.assertEqual(AlertInstance.objects.filter(alert_group=existing_group).count(), initial_instance_count) # Count unchanged
        mock_warning.assert_called_once()
        self.assertIn("Duplicate resolved event detected", mock_warning.call_args[0][0])

    def test_resolved_no_exact_match_marks_latest_open_inferred(self):
        """Scenario: Resolved alert with no exact start_at match, but other open firing instances exist."""
        start_time_old = timezone.now() - datetime.timedelta(hours=2)
        start_time_latest_open = timezone.now() - datetime.timedelta(hours=1)
        start_time_resolved_payload = timezone.now() - datetime.timedelta(minutes=30) # This one doesn't match any open instance

        existing_group = AlertGroup.objects.create(
            fingerprint='resolve-other-open-fg', name='Resolve Other Open', labels={},
            current_status='firing', total_firing_count=2
        )
        old_open_instance = AlertInstance.objects.create(
            alert_group=existing_group, status='firing', started_at=start_time_old,
            ended_at=None, annotations={'summary': 'Old open'}
        )
        latest_open_instance = AlertInstance.objects.create(
            alert_group=existing_group, status='firing', started_at=start_time_latest_open,
            ended_at=None, annotations={'summary': 'Latest open'}
        )

        parsed_data = {
            'fingerprint': 'resolve-other-open-fg', 'status': 'resolved', 'labels': {},
            'starts_at': start_time_resolved_payload, # This start time doesn't match any open instance
            'ends_at': timezone.now() - datetime.timedelta(minutes=10),
            'annotations': {}, 'generator_url': ''
        }

        with patch('alerts.services.alert_state_manager.logger.warning') as mock_warning:
            alert_group, updated_instance = update_alert_state(parsed_data)

        self.assertEqual(alert_group.pk, existing_group.pk)
        alert_group.refresh_from_db()
        self.assertEqual(alert_group.current_status, 'resolved') # Group status should become resolved

        # Check that the latest open instance was marked as inferred resolved
        latest_open_instance.refresh_from_db()
        self.assertEqual(latest_open_instance.status, 'resolved')
        self.assertIsNone(latest_open_instance.ended_at) # ended_at should remain None
        self.assertEqual(latest_open_instance.resolution_type, 'inferred')
        self.assertEqual(updated_instance.pk, latest_open_instance.pk) # The returned instance should be the updated one

        # Check the old open instance is still firing (or was marked inferred by the initial re-fire logic)
        # The re-fire logic at the start of update_alert_state should have marked old_open_instance as inferred
        old_open_instance.refresh_from_db()
        self.assertEqual(old_open_instance.status, 'firing') # This instance should not be marked resolved by this logic
        self.assertIsNone(old_open_instance.ended_at)
        self.assertIsNone(old_open_instance.resolution_type) # This instance is not marked inferred by this resolved logic

        # Check no new instance was created
        self.assertEqual(AlertInstance.objects.filter(alert_group=existing_group).count(), 2) # Two instances, both inferred resolved

        mock_warning.assert_called_once()
        self.assertIn("Received resolved event for AlertGroup", mock_warning.call_args[0][0])
        self.assertIn("no exact firing match found. Marking latest open instance", mock_warning.call_args[0][0])


    def test_resolved_with_none_ends_at_updates_instance_correctly(self):
        """Scenario: Resolved alert with ends_at=None updates existing firing instance."""
        start_time = timezone.now() - datetime.timedelta(minutes=30)
        existing_group = AlertGroup.objects.create(
            fingerprint='resolve-none-end-fg', name='Resolve None End', labels={},
            current_status='firing', total_firing_count=1
        )
        firing_instance = AlertInstance.objects.create(
            alert_group=existing_group, status='firing', started_at=start_time,
            ended_at=None, annotations={}
        )
        parsed_data = {
            'fingerprint': 'resolve-none-end-fg', 'status': 'resolved', 'labels': {},
            'starts_at': start_time, 'ends_at': None, # ends_at is None
            'annotations': {}, 'generator_url': ''
        }

        alert_group, resolved_instance = update_alert_state(parsed_data)

        self.assertEqual(alert_group.pk, existing_group.pk)
        alert_group.refresh_from_db()
        self.assertEqual(alert_group.current_status, 'resolved')

        # Check the existing instance was updated
        self.assertEqual(resolved_instance.pk, firing_instance.pk)
        resolved_instance.refresh_from_db()
        self.assertEqual(resolved_instance.status, 'resolved')
        self.assertEqual(resolved_instance.started_at, start_time)
        self.assertIsNone(resolved_instance.ended_at) # ended_at should remain None
        self.assertEqual(resolved_instance.resolution_type, 'normal') # Should be normal resolution

    @patch('alerts.services.alert_state_manager.AlertGroup.objects.get_or_create')
    def test_exception_handling(self, mock_get_or_create):
        """Scenario: Exception during processing is caught and logged."""
        mock_get_or_create.side_effect = Exception("Simulated database error")

        parsed_data = {
            'fingerprint': 'error-fg', 'status': 'firing', 'labels': {},
            'starts_at': timezone.now(), 'ends_at': None, 'annotations': {}, 'generator_url': ''
        }

        with patch('alerts.services.alert_state_manager.logger.error') as mock_error:
            with self.assertRaises(Exception) as cm:
                update_alert_state(parsed_data)

            self.assertIn("Simulated database error", str(cm.exception))
            mock_error.assert_called_once()
            self.assertIn("Error processing alert update for fingerprint error-fg", mock_error.call_args[0][0])
            self.assertIsNotNone(mock_error.call_args[1]['exc_info']) # Check exc_info is True


# --- Tests for payload_parser.py ---

class ParsePayloadTests(unittest.TestCase): # Inherit from unittest.TestCase

    def _create_sample_alert(self, status='firing', starts_at_offset_mins=-5, ends_at_offset_mins=None, fingerprint='fp1'):
        """Helper to create a single alert structure."""
        now = timezone.now()
        starts_at = now + datetime.timedelta(minutes=starts_at_offset_mins)
        ends_at = None
        if ends_at_offset_mins is not None:
            ends_at = now + datetime.timedelta(minutes=ends_at_offset_mins)
        elif status == 'resolved': # Default resolved end time if not specified
            ends_at = now + datetime.timedelta(minutes=1)

        return {
            "status": status,
            "labels": {
                "alertname": "TestAlert",
                "severity": "warning",
                "instance": "server1",
                "fingerprint_label": fingerprint # Add fingerprint here for clarity if needed
            },
            "annotations": {
                "summary": "This is a test alert.",
                "description": "More details here."
            },
            "startsAt": starts_at.isoformat().replace('+00:00', 'Z'), # RFC3339 format
            "endsAt": ends_at.isoformat().replace('+00:00', 'Z') if ends_at else "0001-01-01T00:00:00Z",
            "generatorURL": f"http://prometheus.example.com/graph?g0.expr={fingerprint}",
            "fingerprint": fingerprint
        }

    def test_valid_v2_payload_multiple_alerts(self):
        """Scenario 1: Valid v2 Payload (Multiple Alerts)."""
        alert1_data = self._create_sample_alert(fingerprint='fp1')
        alert2_data = self._create_sample_alert(status='resolved', ends_at_offset_mins=1, fingerprint='fp2')
        payload = {
            "receiver": "webhook",
            "status": "firing", # Can be firing even if one alert is resolved
            "alerts": [alert1_data, alert2_data],
            "groupLabels": {"alertname": "TestAlert"},
            "commonLabels": {"job": "test"},
            "commonAnnotations": {"dashboard": "http://grafana.example.com"},
            "externalURL": "http://alertmanager.example.com",
            "version": "4",
            "groupKey": "{}:{alertname=\"TestAlert\"}",
            "truncatedAlerts": 0
        }

        parsed_alerts = parse_alertmanager_payload(payload)

        self.assertEqual(len(parsed_alerts), 2)

        # Check alert 1 (firing)
        self.assertEqual(parsed_alerts[0]['fingerprint'], 'fp1')
        self.assertEqual(parsed_alerts[0]['status'], 'firing')
        self.assertEqual(parsed_alerts[0]['labels'], alert1_data['labels'])
        self.assertEqual(parsed_alerts[0]['annotations'], alert1_data['annotations'])
        self.assertIsInstance(parsed_alerts[0]['starts_at'], datetime.datetime)
        self.assertAlmostEqual(parsed_alerts[0]['starts_at'], parse_datetime(alert1_data['startsAt']), delta=datetime.timedelta(seconds=1))
        self.assertIsNone(parsed_alerts[0]['ends_at']) # Because endsAt was zero time
        self.assertEqual(parsed_alerts[0]['generator_url'], alert1_data['generatorURL'])

        # Check alert 2 (resolved)
        self.assertEqual(parsed_alerts[1]['fingerprint'], 'fp2')
        self.assertEqual(parsed_alerts[1]['status'], 'resolved')
        self.assertEqual(parsed_alerts[1]['labels'], alert2_data['labels'])
        self.assertEqual(parsed_alerts[1]['annotations'], alert2_data['annotations'])
        self.assertIsInstance(parsed_alerts[1]['starts_at'], datetime.datetime)
        self.assertIsInstance(parsed_alerts[1]['ends_at'], datetime.datetime)
        self.assertAlmostEqual(parsed_alerts[1]['starts_at'], parse_datetime(alert2_data['startsAt']), delta=datetime.timedelta(seconds=1))
        self.assertAlmostEqual(parsed_alerts[1]['ends_at'], parse_datetime(alert2_data['endsAt']), delta=datetime.timedelta(seconds=1))
        self.assertEqual(parsed_alerts[1]['generator_url'], alert2_data['generatorURL'])

    def test_valid_v1_or_single_alert_payload(self):
        """Scenario 2: Payload structure without top-level 'alerts' key."""
        payload = self._create_sample_alert(fingerprint='single-fp')

        parsed_alerts = parse_alertmanager_payload(payload)

        self.assertEqual(len(parsed_alerts), 1)
        self.assertEqual(parsed_alerts[0]['fingerprint'], 'single-fp')
        self.assertEqual(parsed_alerts[0]['status'], 'firing')
        self.assertIsNone(parsed_alerts[0]['ends_at'])

    def test_status_firing(self):
        """Scenario 3: 'firing' Status."""
        payload = {"alerts": [self._create_sample_alert(status='firing')]}
        parsed = parse_alertmanager_payload(payload)
        self.assertEqual(parsed[0]['status'], 'firing')
        self.assertIsNone(parsed[0]['ends_at'])

    def test_status_resolved_with_valid_endsat(self):
        """Scenario 4: 'resolved' Status with Valid `endsAt`."""
        end_time = timezone.now() + datetime.timedelta(minutes=10)
        alert_data = self._create_sample_alert(status='resolved', ends_at_offset_mins=10)
        payload = {"alerts": [alert_data]}
        parsed = parse_alertmanager_payload(payload)
        self.assertEqual(parsed[0]['status'], 'resolved')
        self.assertIsInstance(parsed[0]['ends_at'], datetime.datetime)
        self.assertAlmostEqual(parsed[0]['ends_at'], end_time, delta=datetime.timedelta(seconds=1))

    def test_status_resolved_with_zero_endsat(self):
        """Scenario 5: 'resolved' Status with Zero `endsAt`."""
        alert_data = self._create_sample_alert(status='resolved')
        alert_data['endsAt'] = "0001-01-01T00:00:00Z" # Explicit zero time
        payload = {"alerts": [alert_data]}
        parsed = parse_alertmanager_payload(payload)
        self.assertEqual(parsed[0]['status'], 'resolved')
        self.assertIsNone(parsed[0]['ends_at'])

    def test_missing_optional_fields(self):
        """Scenario 6: Missing Optional Fields."""
        alert_data = self._create_sample_alert()
        del alert_data['annotations']
        del alert_data['generatorURL']
        payload = {"alerts": [alert_data]}
        parsed = parse_alertmanager_payload(payload)
        self.assertEqual(parsed[0]['annotations'], {}) # Should default to empty dict
        self.assertIsNone(parsed[0]['generator_url']) # Should be None

    def test_empty_alerts_list(self):
        """Scenario 7: Empty `alerts` List."""
        payload = { "receiver": "webhook", "status": "resolved", "alerts": [] }
        parsed = parse_alertmanager_payload(payload)
        self.assertEqual(parsed, [])

    def test_invalid_date_format(self):
        """Scenario 8: Invalid Date Format."""
        alert_data = self._create_sample_alert()
        alert_data['startsAt'] = "this-is-not-a-date"
        payload = {"alerts": [alert_data]}
        # dateutil.parser raises ValueError for unparseable dates
        with self.assertRaises(ValueError):
            parse_alertmanager_payload(payload)