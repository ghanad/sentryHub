import datetime
import time
import copy
from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone

# Import models from the parent 'alerts' app
from ..models import SilenceRule, AlertGroup, AlertInstance

# Import services from the parent 'alerts' app
from ..services.silence_matcher import check_alert_silence
from ..services.alerts_processor import process_alert, extract_alert_data


class SilenceMatcherServiceTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.test_user = User.objects.create_user(username='silenceuser', password='password')

    def setUp(self):
        """Create a base alert group for tests."""
        self.alert_group = AlertGroup.objects.create(
            fingerprint="silence_test_fp",
            name="Silence Test Alert",
            labels={"job": "api", "severity": "critical", "dc": "us-east-1"}
        )

    def _create_silence(self, matchers, start_delta_mins=-5, end_delta_mins=60, comment="Test Silence"):
        """Helper to create a silence rule relative to now."""
        now = timezone.now()
        starts_at = now + datetime.timedelta(minutes=start_delta_mins)
        ends_at = now + datetime.timedelta(minutes=end_delta_mins)
        return SilenceRule.objects.create(
            matchers=matchers,
            starts_at=starts_at,
            ends_at=ends_at,
            comment=comment,
            created_by=self.test_user
        )

    def test_no_active_rules(self):
        """Test check_alert_silence when no active rules exist."""
        # Create an inactive rule (ends in the past)
        self._create_silence({"job": "api"}, start_delta_mins=-60, end_delta_mins=-30)
        # Create a future rule
        self._create_silence({"job": "api"}, start_delta_mins=10, end_delta_mins=30)

        result = check_alert_silence(self.alert_group)
        self.alert_group.refresh_from_db()

        self.assertFalse(result)
        self.assertFalse(self.alert_group.is_silenced)
        self.assertIsNone(self.alert_group.silenced_until)

    def test_active_rule_no_match_value(self):
        """Test check_alert_silence with an active rule that doesn't match (value mismatch)."""
        self._create_silence({"job": "worker"}) # Active, but job label is different

        result = check_alert_silence(self.alert_group)
        self.alert_group.refresh_from_db()

        self.assertFalse(result)
        self.assertFalse(self.alert_group.is_silenced)
        self.assertIsNone(self.alert_group.silenced_until)

    def test_active_rule_no_match_key(self):
        """Test check_alert_silence with an active rule that doesn't match (key mismatch)."""
        self._create_silence({"service": "api"}) # Active, but alert has 'job', not 'service'

        result = check_alert_silence(self.alert_group)
        self.alert_group.refresh_from_db()

        self.assertFalse(result)
        self.assertFalse(self.alert_group.is_silenced)
        self.assertIsNone(self.alert_group.silenced_until)

    def test_active_rule_exact_match(self):
        """Test check_alert_silence with an active rule that exactly matches."""
        rule = self._create_silence({"job": "api", "severity": "critical", "dc": "us-east-1"})

        result = check_alert_silence(self.alert_group)
        self.alert_group.refresh_from_db()

        self.assertTrue(result)
        self.assertTrue(self.alert_group.is_silenced)
        self.assertEqual(self.alert_group.silenced_until, rule.ends_at)

    def test_active_rule_subset_match(self):
        """Test check_alert_silence with an active rule whose matchers are a subset of alert labels."""
        rule = self._create_silence({"job": "api", "dc": "us-east-1"}) # Matches subset

        result = check_alert_silence(self.alert_group)
        self.alert_group.refresh_from_db()

        self.assertTrue(result)
        self.assertTrue(self.alert_group.is_silenced)
        self.assertEqual(self.alert_group.silenced_until, rule.ends_at)

    def test_active_rule_superset_no_match(self):
        """Test check_alert_silence with an active rule whose matchers are a superset (should not match)."""
        self._create_silence({"job": "api", "dc": "us-east-1", "extra_label": "value"}) # Rule has extra label

        result = check_alert_silence(self.alert_group)
        self.alert_group.refresh_from_db()

        self.assertFalse(result)
        self.assertFalse(self.alert_group.is_silenced)
        self.assertIsNone(self.alert_group.silenced_until)

    def test_multiple_active_rules_one_match(self):
        """Test with multiple active rules where only one matches."""
        self._create_silence({"job": "worker"}) # Active, no match
        rule_match = self._create_silence({"severity": "critical", "dc": "us-east-1"}) # Active, match
        self._create_silence({"job": "api", "instance": "server1"}) # Active, no match

        result = check_alert_silence(self.alert_group)
        self.alert_group.refresh_from_db()

        self.assertTrue(result)
        self.assertTrue(self.alert_group.is_silenced)
        self.assertEqual(self.alert_group.silenced_until, rule_match.ends_at)

    def test_multiple_active_rules_multiple_matches_latest_end_time(self):
        """Test with multiple matching active rules, ensures latest end time is used."""
        now = timezone.now()
        rule1_ends = now + datetime.timedelta(minutes=30)
        rule2_ends = now + datetime.timedelta(minutes=60) # Later end time
        rule3_ends = now + datetime.timedelta(minutes=45)

        self._create_silence({"job": "api"}, end_delta_mins=30) # Match 1
        rule_latest = self._create_silence({"dc": "us-east-1"}, end_delta_mins=60) # Match 2 (latest end)
        self._create_silence({"severity": "critical"}, end_delta_mins=45) # Match 3

        result = check_alert_silence(self.alert_group)
        self.alert_group.refresh_from_db()

        self.assertTrue(result)
        self.assertTrue(self.alert_group.is_silenced)
        # Should be silenced until the end time of rule_latest
        self.assertAlmostEqual(self.alert_group.silenced_until, rule_latest.ends_at, delta=datetime.timedelta(seconds=1))

    def test_alert_becomes_unsilenced_when_rule_expires(self):
        """Test that an alert becomes unsilenced after the rule expires."""
        # Create an active rule that will expire soon
        rule = self._create_silence({"job": "api"}, start_delta_mins=-10, end_delta_mins=1) # Ends in 1 min

        # Initial check: should be silenced
        result1 = check_alert_silence(self.alert_group)
        self.alert_group.refresh_from_db()
        self.assertTrue(result1)
        self.assertTrue(self.alert_group.is_silenced)
        self.assertEqual(self.alert_group.silenced_until, rule.ends_at)

        # Simulate time passing beyond the rule's end time
        # Instead of sleeping, we can manually expire the rule for testing
        rule.ends_at = timezone.now() - datetime.timedelta(seconds=1)
        rule.save()

        # Second check: should no longer be silenced
        result2 = check_alert_silence(self.alert_group)
        self.alert_group.refresh_from_db()
        self.assertFalse(result2)
        self.assertFalse(self.alert_group.is_silenced)
        self.assertIsNone(self.alert_group.silenced_until)

    def test_alert_becomes_silenced_when_rule_becomes_active(self):
        """Test that an alert becomes silenced when a matching rule becomes active."""
        # Create a future rule
        future_start = timezone.now() + datetime.timedelta(minutes=1)
        future_end = future_start + datetime.timedelta(hours=1)
        rule = SilenceRule.objects.create(
            matchers={"job": "api"},
            starts_at=future_start,
            ends_at=future_end,
            comment="Future Rule",
            created_by=self.test_user
        )

        # Initial check: should not be silenced
        result1 = check_alert_silence(self.alert_group)
        self.alert_group.refresh_from_db()
        self.assertFalse(result1)
        self.assertFalse(self.alert_group.is_silenced)

        # Simulate time passing so the rule becomes active
        rule.starts_at = timezone.now() - datetime.timedelta(seconds=1)
        rule.save()

        # Second check: should now be silenced
        result2 = check_alert_silence(self.alert_group)
        self.alert_group.refresh_from_db()
        self.assertTrue(result2)
        self.assertTrue(self.alert_group.is_silenced)
        self.assertEqual(self.alert_group.silenced_until, rule.ends_at)

    def test_rule_with_invalid_matchers_is_skipped(self):
        """Test that rules with invalid or empty matchers are ignored."""
        # Create potentially invalid/empty rules (DB constraints might prevent some)
        # self._create_silence(matchers=None) # DB prevents creating None matchers
        try:
            # Attempt to create with list, might fail depending on DB JSON handling
            self._create_silence(matchers=[]) # Invalid type for matching logic
        except Exception:
             # If DB prevents storing list, we can't test this specific invalid type directly
             pass
        self._create_silence(matchers={}) # Valid but empty, should not match anything implicitly

        # Create a valid matching rule to ensure it still works
        valid_rule = self._create_silence({"job": "api"})

        result = check_alert_silence(self.alert_group)
        self.alert_group.refresh_from_db()

        # Should be silenced by the valid rule
        self.assertTrue(result)
        self.assertTrue(self.alert_group.is_silenced)
        self.assertEqual(self.alert_group.silenced_until, valid_rule.ends_at)

    def test_already_silenced_update_to_later_end_time(self):
        """Test updating silenced_until if a new matching rule ends later."""
        now = timezone.now()
        # Initial silencing rule
        rule1 = self._create_silence({"job": "api"}, end_delta_mins=30)
        
        # Check initial silence
        check_alert_silence(self.alert_group)
        self.alert_group.refresh_from_db()
        self.assertTrue(self.alert_group.is_silenced)
        self.assertAlmostEqual(self.alert_group.silenced_until, rule1.ends_at, delta=datetime.timedelta(seconds=1))

        # Create a new rule that also matches but ends later
        rule2 = self._create_silence({"dc": "us-east-1"}, end_delta_mins=60)

        # Check again
        result = check_alert_silence(self.alert_group)
        self.alert_group.refresh_from_db()

        self.assertTrue(result)
        self.assertTrue(self.alert_group.is_silenced)
        # silenced_until should now be updated to rule2's end time
        self.assertAlmostEqual(self.alert_group.silenced_until, rule2.ends_at, delta=datetime.timedelta(seconds=1))

    def test_already_silenced_no_update_if_new_rule_ends_earlier(self):
        """Test silenced_until is not updated if a new matching rule ends earlier."""
        now = timezone.now()
        # Initial silencing rule (ends later)
        rule1 = self._create_silence({"job": "api"}, end_delta_mins=60)

        # Check initial silence
        check_alert_silence(self.alert_group)
        self.alert_group.refresh_from_db()
        self.assertTrue(self.alert_group.is_silenced)
        initial_silenced_until = self.alert_group.silenced_until
        self.assertAlmostEqual(initial_silenced_until, rule1.ends_at, delta=datetime.timedelta(seconds=1))

        # Create a new rule that also matches but ends earlier
        self._create_silence({"dc": "us-east-1"}, end_delta_mins=30)

        # Check again
        result = check_alert_silence(self.alert_group)
        self.alert_group.refresh_from_db()

        self.assertTrue(result)
        self.assertTrue(self.alert_group.is_silenced)
        # silenced_until should NOT have changed
        self.assertEqual(self.alert_group.silenced_until, initial_silenced_until)


# Mock the documentation matcher function
@patch('alerts.services.alerts_processor.match_documentation_to_alert', return_value=None)
class AlertProcessorServiceTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.test_user = User.objects.create_user(username='procuser', password='password')
        # Define sample alert data structures
        cls.sample_labels = {"alertname": "TestCPUUsage", "job": "node_exporter", "instance": "server1", "severity": "warning"}
        cls.sample_annotations = {"summary": "High CPU usage detected", "description": "CPU usage is above 90%"}
        cls.sample_generator_url = "http://prometheus/graph?g0.expr=cpu_usage"
        cls.sample_fingerprint = "fingerprint123abc"

    def _get_alert_data(self, status, fingerprint, labels, annotations, starts_at_str, ends_at_str, generator_url):
        """Helper to create alert data dictionary."""
        return {
            "status": status,
            "labels": labels,
            "annotations": annotations,
            "startsAt": starts_at_str,
            "endsAt": ends_at_str,
            "generatorURL": generator_url,
            "fingerprint": fingerprint
        }

    def _create_silence(self, matchers, start_delta_mins=-5, end_delta_mins=60, comment="Test Silence"):
        """Helper to create a silence rule relative to now."""
        now = timezone.now()
        starts_at = now + datetime.timedelta(minutes=start_delta_mins)
        ends_at = now + datetime.timedelta(minutes=end_delta_mins)
        return SilenceRule.objects.create(
            matchers=matchers,
            starts_at=starts_at,
            ends_at=ends_at,
            comment=comment,
            created_by=self.test_user
        )

    def test_process_first_firing_alert(self, mock_match_doc):
        """Test processing the very first firing alert for a fingerprint."""
        start_time_str = "2023-10-27T10:00:00Z"
        alert_data = self._get_alert_data(
            "firing", self.sample_fingerprint, self.sample_labels, self.sample_annotations,
            start_time_str, "0001-01-01T00:00:00Z", self.sample_generator_url
        )

        alert_group = process_alert(alert_data)

        self.assertIsInstance(alert_group, AlertGroup)
        self.assertEqual(alert_group.fingerprint, self.sample_fingerprint)
        self.assertEqual(alert_group.name, "TestCPUUsage")
        self.assertEqual(alert_group.labels, self.sample_labels)
        self.assertEqual(alert_group.current_status, "firing")
        self.assertEqual(alert_group.total_firing_count, 1)
        self.assertFalse(alert_group.acknowledged)
        self.assertFalse(alert_group.is_silenced) # Assuming no silence rule

        # Check instance creation
        self.assertEqual(alert_group.instances.count(), 1)
        instance = alert_group.instances.first()
        self.assertEqual(instance.status, "firing")
        # Use UTC for comparison as parse_datetime creates UTC from 'Z' suffix
        self.assertEqual(instance.started_at, datetime.datetime(2023, 10, 27, 10, 0, 0, tzinfo=datetime.timezone.utc))
        self.assertIsNone(instance.ended_at)
        self.assertEqual(instance.annotations, self.sample_annotations)
        self.assertIsNone(instance.resolution_type)

        mock_match_doc.assert_called_once_with(alert_group)

    def test_process_duplicate_firing_alert(self, mock_match_doc):
        """Test processing a duplicate firing alert (same start time)."""
        start_time_str = "2023-10-27T10:00:00Z"
        alert_data = self._get_alert_data(
            "firing", self.sample_fingerprint, self.sample_labels, self.sample_annotations,
            start_time_str, "0001-01-01T00:00:00Z", self.sample_generator_url
        )

        # Process first time
        alert_group1 = process_alert(alert_data)
        instance_count1 = AlertInstance.objects.count()
        last_occurrence1 = alert_group1.last_occurrence

        # Ensure some time passes for last_occurrence check
        time.sleep(0.01)

        # Process second time (duplicate)
        alert_group2 = process_alert(alert_data)
        instance_count2 = AlertInstance.objects.count()

        self.assertEqual(alert_group1.pk, alert_group2.pk) # Should be the same group
        self.assertEqual(instance_count1, instance_count2) # No new instance created
        self.assertEqual(alert_group2.total_firing_count, 1) # Count not incremented
        self.assertTrue(alert_group2.last_occurrence > last_occurrence1) # last_occurrence updated
        self.assertEqual(mock_match_doc.call_count, 2) # Called each time

    def test_process_new_firing_alert_different_start_time(self, mock_match_doc):
        """Test processing a new firing alert for the same group but different start time."""
        start_time1_str = "2023-10-27T10:00:00Z"
        start_time2_str = "2023-10-27T10:10:00Z" # Later start time
        alert_data1 = self._get_alert_data(
            "firing", self.sample_fingerprint, self.sample_labels, self.sample_annotations,
            start_time1_str, "0001-01-01T00:00:00Z", self.sample_generator_url
        )
        alert_data2 = self._get_alert_data(
            "firing", self.sample_fingerprint, self.sample_labels, self.sample_annotations,
            start_time2_str, "0001-01-01T00:00:00Z", self.sample_generator_url
        )

        # Process first firing
        alert_group = process_alert(alert_data1)
        # Use UTC for lookup
        instance1 = alert_group.instances.get(started_at=datetime.datetime(2023, 10, 27, 10, 0, 0, tzinfo=datetime.timezone.utc))
        self.assertEqual(alert_group.total_firing_count, 1)

        # Process second firing (different start time)
        alert_group = process_alert(alert_data2)

        # Check first instance - should be resolved (inferred)
        instance1.refresh_from_db()
        self.assertEqual(instance1.status, "resolved")
        self.assertEqual(instance1.resolution_type, "inferred")
        self.assertIsNone(instance1.ended_at) # ended_at is None for inferred

        # Check second instance - should be created and firing
        self.assertEqual(alert_group.instances.count(), 2)
        # Use UTC for lookup
        instance2 = alert_group.instances.get(started_at=datetime.datetime(2023, 10, 27, 10, 10, 0, tzinfo=datetime.timezone.utc))
        self.assertEqual(instance2.status, "firing")
        self.assertIsNone(instance2.ended_at)
        self.assertIsNone(instance2.resolution_type)

        # Check group
        self.assertEqual(alert_group.current_status, "firing")
        self.assertEqual(alert_group.total_firing_count, 2) # Incremented
        self.assertEqual(mock_match_doc.call_count, 2)

    def test_process_resolved_alert_matching_firing(self, mock_match_doc):
        """Test processing a resolved alert that matches an active firing instance."""
        start_time_str = "2023-10-27T10:00:00Z"
        end_time_str = "2023-10-27T10:05:00Z"
        firing_alert_data = self._get_alert_data(
            "firing", self.sample_fingerprint, self.sample_labels, self.sample_annotations,
            start_time_str, "0001-01-01T00:00:00Z", self.sample_generator_url
        )
        resolved_alert_data = self._get_alert_data(
            "resolved", self.sample_fingerprint, self.sample_labels, self.sample_annotations,
            start_time_str, end_time_str, self.sample_generator_url
        )

        # Process firing
        alert_group = process_alert(firing_alert_data)
        instance = alert_group.instances.first()
        self.assertEqual(alert_group.instances.count(), 1)
        self.assertEqual(instance.status, "firing")

        # Process resolved
        alert_group = process_alert(resolved_alert_data)

        # Check instance - should be updated to resolved
        instance.refresh_from_db()
        self.assertEqual(alert_group.instances.count(), 1) # No new instance
        self.assertEqual(instance.status, "resolved")
        self.assertEqual(instance.resolution_type, "normal")
        # Use UTC for comparison
        self.assertEqual(instance.ended_at, datetime.datetime(2023, 10, 27, 10, 5, 0, tzinfo=datetime.timezone.utc))

        # Check group
        self.assertEqual(alert_group.current_status, "resolved")
        self.assertEqual(mock_match_doc.call_count, 2)

    def test_process_resolved_alert_no_matching_firing_but_active_exist(self, mock_match_doc):
        """Test resolved alert closes other active instances if no start time match."""
        start_time1_str = "2023-10-27T10:00:00Z"
        start_time2_str = "2023-10-27T10:10:00Z" # A different active firing instance
        resolve_start_time_str = "2023-10-27T09:55:00Z" # Start time of the resolve message (doesn't match active)
        resolve_end_time_str = "2023-10-27T10:15:00Z"

        firing_alert_data1 = self._get_alert_data(
            "firing", self.sample_fingerprint, self.sample_labels, self.sample_annotations,
            start_time1_str, "0001-01-01T00:00:00Z", self.sample_generator_url
        )
        firing_alert_data2 = self._get_alert_data(
            "firing", self.sample_fingerprint, self.sample_labels, self.sample_annotations,
            start_time2_str, "0001-01-01T00:00:00Z", self.sample_generator_url
        )
        resolved_alert_data = self._get_alert_data(
            "resolved", self.sample_fingerprint, self.sample_labels, self.sample_annotations,
            resolve_start_time_str, resolve_end_time_str, self.sample_generator_url
        )

        # Process two firing alerts
        process_alert(firing_alert_data1)
        alert_group = process_alert(firing_alert_data2) # This infers resolution for instance 1
        # Use UTC for lookup
        instance1 = alert_group.instances.get(started_at=datetime.datetime(2023, 10, 27, 10, 0, 0, tzinfo=datetime.timezone.utc))
        instance2 = alert_group.instances.get(started_at=datetime.datetime(2023, 10, 27, 10, 10, 0, tzinfo=datetime.timezone.utc))
        instance1.status = 'firing' # Manually set instance1 back to firing for test scenario
        instance1.resolution_type = None
        instance1.ended_at = None
        instance1.save()
        self.assertEqual(alert_group.instances.filter(status='firing', ended_at__isnull=True).count(), 2)

        # Process resolved alert (doesn't match start time of instance1 or instance2)
        alert_group = process_alert(resolved_alert_data)

        # Check instances - both previously active firing instances should be resolved now
        instance1.refresh_from_db()
        instance2.refresh_from_db()
        self.assertEqual(instance1.status, "resolved")
        self.assertEqual(instance1.resolution_type, "normal") # Resolved by the incoming message
        # Use UTC for comparison
        self.assertEqual(instance1.ended_at, datetime.datetime(2023, 10, 27, 10, 15, 0, tzinfo=datetime.timezone.utc))
        self.assertEqual(instance2.status, "resolved")
        self.assertEqual(instance2.resolution_type, "normal") # Resolved by the incoming message
        # Use UTC for comparison
        self.assertEqual(instance2.ended_at, datetime.datetime(2023, 10, 27, 10, 15, 0, tzinfo=datetime.timezone.utc))

        # Check if a new resolved instance was created for the specific resolve message times
        # Use UTC for filter
        self.assertTrue(alert_group.instances.filter(
            status='resolved',
            started_at=datetime.datetime(2023, 10, 27, 9, 55, 0, tzinfo=datetime.timezone.utc),
            ended_at=datetime.datetime(2023, 10, 27, 10, 15, 0, tzinfo=datetime.timezone.utc)
        ).exists())
        self.assertEqual(alert_group.instances.count(), 3) # instance1, instance2, plus the new one

        # Check group
        self.assertEqual(alert_group.current_status, "resolved")
        self.assertEqual(mock_match_doc.call_count, 3)

    def test_process_resolved_alert_no_active_firing(self, mock_match_doc):
        """Test processing a resolved alert when no firing instances exist."""
        start_time_str = "2023-10-27T10:00:00Z"
        end_time_str = "2023-10-27T10:05:00Z"
        resolved_alert_data = self._get_alert_data(
            "resolved", self.sample_fingerprint, self.sample_labels, self.sample_annotations,
            start_time_str, end_time_str, self.sample_generator_url
        )

        # Ensure no group/instance exists initially
        AlertGroup.objects.filter(fingerprint=self.sample_fingerprint).delete()

        # Process resolved
        alert_group = process_alert(resolved_alert_data)

        # Check instance - a new resolved instance should be created
        self.assertEqual(alert_group.instances.count(), 1)
        instance = alert_group.instances.first()
        self.assertEqual(instance.status, "resolved")
        self.assertEqual(instance.resolution_type, "normal")
        # Use UTC for comparison
        self.assertEqual(instance.started_at, datetime.datetime(2023, 10, 27, 10, 0, 0, tzinfo=datetime.timezone.utc))
        self.assertEqual(instance.ended_at, datetime.datetime(2023, 10, 27, 10, 5, 0, tzinfo=datetime.timezone.utc))

        # Check group
        self.assertEqual(alert_group.current_status, "resolved")
        self.assertEqual(alert_group.total_firing_count, 1) # Created with count 1
        self.assertEqual(mock_match_doc.call_count, 1)

    def test_process_duplicate_resolved_alert(self, mock_match_doc):
        """Test processing a duplicate resolved alert."""
        start_time_str = "2023-10-27T10:00:00Z"
        end_time_str = "2023-10-27T10:05:00Z"
        resolved_alert_data = self._get_alert_data(
            "resolved", self.sample_fingerprint, self.sample_labels, self.sample_annotations,
            start_time_str, end_time_str, self.sample_generator_url
        )

        # Process first time
        alert_group1 = process_alert(resolved_alert_data)
        instance_count1 = AlertInstance.objects.count()

        # Process second time (duplicate)
        alert_group2 = process_alert(resolved_alert_data)
        instance_count2 = AlertInstance.objects.count()

        self.assertEqual(alert_group1.pk, alert_group2.pk)
        self.assertEqual(instance_count1, instance_count2) # No new instance
        self.assertEqual(mock_match_doc.call_count, 2) # Called each time

    def test_process_firing_after_resolve_resets_ack(self, mock_match_doc):
        """Test that a new firing alert resets acknowledgement."""
        start_time1_str = "2023-10-27T10:00:00Z"
        end_time1_str = "2023-10-27T10:05:00Z"
        start_time2_str = "2023-10-27T10:10:00Z" # New firing start

        firing1_data = self._get_alert_data("firing", self.sample_fingerprint, self.sample_labels, self.sample_annotations, start_time1_str, "0001-01-01T00:00:00Z", self.sample_generator_url)
        resolved1_data = self._get_alert_data("resolved", self.sample_fingerprint, self.sample_labels, self.sample_annotations, start_time1_str, end_time1_str, self.sample_generator_url)
        firing2_data = self._get_alert_data("firing", self.sample_fingerprint, self.sample_labels, self.sample_annotations, start_time2_str, "0001-01-01T00:00:00Z", self.sample_generator_url)

        # Process first firing
        alert_group = process_alert(firing1_data)

        # Acknowledge it
        alert_group.acknowledged = True
        alert_group.acknowledged_by = self.test_user
        alert_group.acknowledgement_time = timezone.now()
        alert_group.save()

        # Process resolution
        alert_group = process_alert(resolved1_data)
        self.assertTrue(alert_group.acknowledged) # Ack remains after resolve

        # Process second firing
        alert_group = process_alert(firing2_data)

        # Check acknowledgement - should be reset
        self.assertFalse(alert_group.acknowledged)
        self.assertIsNone(alert_group.acknowledged_by)
        self.assertIsNone(alert_group.acknowledgement_time)
        self.assertEqual(alert_group.current_status, "firing")
        self.assertEqual(alert_group.total_firing_count, 2) # Incremented

        # Check instances
        self.assertEqual(alert_group.instances.count(), 2)
        # Use UTC for lookup
        instance1 = alert_group.instances.get(started_at=datetime.datetime(2023, 10, 27, 10, 0, 0, tzinfo=datetime.timezone.utc))
        instance2 = alert_group.instances.get(started_at=datetime.datetime(2023, 10, 27, 10, 10, 0, tzinfo=datetime.timezone.utc))
        self.assertEqual(instance1.status, "resolved")
        self.assertEqual(instance2.status, "firing")
        self.assertEqual(mock_match_doc.call_count, 3)

    def test_process_firing_alert_when_silenced(self, mock_match_doc):
        """Test processing a firing alert that matches an active silence rule."""
        start_time_str = "2023-10-27T10:00:00Z"
        alert_data = self._get_alert_data(
            "firing", self.sample_fingerprint, self.sample_labels, self.sample_annotations,
            start_time_str, "0001-01-01T00:00:00Z", self.sample_generator_url
        )

        # Create a matching active silence rule
        silence_rule = self._create_silence(matchers={"job": "node_exporter"})

        alert_group = process_alert(alert_data)

        # Check group status - should be firing, but marked as silenced
        self.assertEqual(alert_group.current_status, "firing")
        self.assertTrue(alert_group.is_silenced)
        self.assertEqual(alert_group.silenced_until, silence_rule.ends_at)

        # Check instance - should still be created
        self.assertEqual(alert_group.instances.count(), 1)
        instance = alert_group.instances.first()
        self.assertEqual(instance.status, "firing")

        mock_match_doc.assert_called_once_with(alert_group)

    def test_process_resolved_alert_when_silenced(self, mock_match_doc):
        """Test processing a resolved alert when a silence rule was active."""
        start_time_str = "2023-10-27T10:00:00Z"
        end_time_str = "2023-10-27T10:05:00Z"
        firing_alert_data = self._get_alert_data(
            "firing", self.sample_fingerprint, self.sample_labels, self.sample_annotations,
            start_time_str, "0001-01-01T00:00:00Z", self.sample_generator_url
        )
        resolved_alert_data = self._get_alert_data(
            "resolved", self.sample_fingerprint, self.sample_labels, self.sample_annotations,
            start_time_str, end_time_str, self.sample_generator_url
        )

        # Create a matching active silence rule
        silence_rule = self._create_silence(matchers={"job": "node_exporter"})

        # Process firing (gets silenced)
        alert_group = process_alert(firing_alert_data)
        self.assertTrue(alert_group.is_silenced)

        # Process resolved
        alert_group = process_alert(resolved_alert_data)

        # Check group status - should be resolved
        self.assertEqual(alert_group.current_status, "resolved")
        # Silence status depends on whether the rule is still active *now*
        # Re-run check_alert_silence to get the current state
        is_currently_silenced = check_alert_silence(alert_group)
        alert_group.refresh_from_db() # Refresh after check_alert_silence might save
        self.assertEqual(alert_group.is_silenced, is_currently_silenced)
        if is_currently_silenced:
             self.assertEqual(alert_group.silenced_until, silence_rule.ends_at)
        else:
             self.assertIsNone(alert_group.silenced_until)


        # Check instance - should be resolved
        self.assertEqual(alert_group.instances.count(), 1)
        instance = alert_group.instances.first()
        self.assertEqual(instance.status, "resolved")
        self.assertEqual(instance.resolution_type, "normal")

        self.assertEqual(mock_match_doc.call_count, 2)

    # --- Tests for extract_alert_data ---

    def test_extract_alert_data_full(self, mock_match_doc): # mock_match_doc is unused but required by @patch
        """Test extract_alert_data with all fields present."""
        start_time_str = "2023-10-27T10:00:00Z"
        end_time_str = "2023-10-27T10:05:00Z"
        alert_data = self._get_alert_data(
            "resolved", self.sample_fingerprint, self.sample_labels, self.sample_annotations,
            start_time_str, end_time_str, self.sample_generator_url
        )
        
        fingerprint, status, labels, annotations, starts_at, ends_at, generator_url = extract_alert_data(alert_data)
        
        self.assertEqual(fingerprint, self.sample_fingerprint)
        self.assertEqual(status, "resolved")
        self.assertEqual(labels, self.sample_labels)
        self.assertEqual(annotations, self.sample_annotations)
        self.assertEqual(starts_at, datetime.datetime(2023, 10, 27, 10, 0, 0, tzinfo=datetime.timezone.utc))
        self.assertEqual(ends_at, datetime.datetime(2023, 10, 27, 10, 5, 0, tzinfo=datetime.timezone.utc))
        self.assertEqual(generator_url, self.sample_generator_url)

    def test_extract_alert_data_missing_optional(self, mock_match_doc): # mock_match_doc is unused
        """Test extract_alert_data with missing optional fields."""
        start_time_str = "2023-10-27T10:00:00Z"
        alert_data = {
            "status": "firing",
            "labels": self.sample_labels,
            "annotations": {}, # Empty annotations
            "startsAt": start_time_str,
            # "endsAt": missing
            # "generatorURL": missing
            "fingerprint": self.sample_fingerprint
        }
        
        fingerprint, status, labels, annotations, starts_at, ends_at, generator_url = extract_alert_data(alert_data)
        
        self.assertEqual(fingerprint, self.sample_fingerprint)
        self.assertEqual(status, "firing")
        self.assertEqual(labels, self.sample_labels)
        self.assertEqual(annotations, {}) # Check empty dict
        self.assertEqual(starts_at, datetime.datetime(2023, 10, 27, 10, 0, 0, tzinfo=datetime.timezone.utc))
        self.assertIsNone(ends_at) # Should be None
        self.assertIsNone(generator_url) # Should be None

    def test_extract_alert_data_zero_ends_at(self, mock_match_doc): # mock_match_doc is unused
        """Test extract_alert_data with the zero value for endsAt."""
        start_time_str = "2023-10-27T10:00:00Z"
        zero_end_time_str = "0001-01-01T00:00:00Z"
        alert_data = self._get_alert_data(
            "firing", self.sample_fingerprint, self.sample_labels, self.sample_annotations,
            start_time_str, zero_end_time_str, self.sample_generator_url
        )
        
        fingerprint, status, labels, annotations, starts_at, ends_at, generator_url = extract_alert_data(alert_data)
        
        self.assertEqual(fingerprint, self.sample_fingerprint)
        self.assertEqual(status, "firing")
        self.assertEqual(labels, self.sample_labels)
        self.assertEqual(annotations, self.sample_annotations)
        self.assertEqual(starts_at, datetime.datetime(2023, 10, 27, 10, 0, 0, tzinfo=datetime.timezone.utc))
        self.assertIsNone(ends_at) # Should be None due to zero value check
        self.assertEqual(generator_url, self.sample_generator_url)

    def test_extract_alert_data_empty_labels_annotations(self, mock_match_doc): # mock_match_doc is unused
        """Test extract_alert_data with empty labels and annotations."""
        start_time_str = "2023-10-27T10:00:00Z"
        alert_data = {
            "status": "firing",
            "labels": {}, # Empty labels
            "annotations": {}, # Empty annotations
            "startsAt": start_time_str,
            "endsAt": "0001-01-01T00:00:00Z",
            "generatorURL": self.sample_generator_url,
            "fingerprint": self.sample_fingerprint
        }
        
        fingerprint, status, labels, annotations, starts_at, ends_at, generator_url = extract_alert_data(alert_data)
        
        self.assertEqual(fingerprint, self.sample_fingerprint)
        self.assertEqual(status, "firing")
        self.assertEqual(labels, {})
        self.assertEqual(annotations, {})
        self.assertEqual(starts_at, datetime.datetime(2023, 10, 27, 10, 0, 0, tzinfo=datetime.timezone.utc))
        self.assertIsNone(ends_at)
        self.assertEqual(generator_url, self.sample_generator_url)
