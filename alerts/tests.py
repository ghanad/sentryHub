import datetime
import json # Added for form tests
import time # Added for ordering fixes
import copy # Added for deepcopying alert data
from unittest.mock import patch # Added for mocking
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from django import forms # Added for widget test
# Import models
from .models import SilenceRule, AlertGroup, AlertInstance, AlertComment, AlertAcknowledgementHistory
# Import forms
from .forms import SilenceRuleForm, AlertAcknowledgementForm, AlertCommentForm
# Import services
from .services.silence_matcher import check_alert_silence
# Import specific functions from alerts_processor for targeted testing
from .services.alerts_processor import process_alert, extract_alert_data 
# Assuming AlertDocumentation is in docs app, adjust if different
# from docs.models import AlertDocumentation


class SilenceRuleModelTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Create a user that can be used across multiple tests
        cls.test_user = User.objects.create_user(username='testuser', password='password')

    def test_silence_rule_creation_with_user(self):
        """
        Test that a SilenceRule can be created successfully with valid data
        and a creator user.
        """
        now = timezone.now()
        starts = now + datetime.timedelta(hours=1)
        ends = now + datetime.timedelta(hours=2)
        matchers = {"job": "node_exporter", "instance": "server1"}
        comment = "Test silence rule"

        rule = SilenceRule.objects.create(
            matchers=matchers,
            starts_at=starts,
            ends_at=ends,
            comment=comment,
            created_by=self.test_user
        )

        self.assertIsInstance(rule, SilenceRule)
        self.assertEqual(rule.matchers, matchers)
        self.assertEqual(rule.starts_at, starts)
        self.assertEqual(rule.ends_at, ends)
        self.assertEqual(rule.comment, comment)
        self.assertEqual(rule.created_by, self.test_user)
        self.assertIsNotNone(rule.created_at)
        self.assertIsNotNone(rule.updated_at)

    def test_silence_rule_creation_without_user(self):
        """
        Test that a SilenceRule can be created successfully without a creator user.
        """
        now = timezone.now()
        starts = now + datetime.timedelta(minutes=5)
        ends = now + datetime.timedelta(minutes=15)
        matchers = {"severity": "critical"}
        comment = "System generated silence"

        rule = SilenceRule.objects.create(
            matchers=matchers,
            starts_at=starts,
            ends_at=ends,
            comment=comment,
            created_by=None # Explicitly set to None
        )

        self.assertIsInstance(rule, SilenceRule)
        self.assertEqual(rule.matchers, matchers)
        self.assertIsNone(rule.created_by)

    def test_is_active_before_start(self):
        """Test is_active() returns False when now is before starts_at."""
        now = timezone.now()
        starts = now + datetime.timedelta(minutes=10)
        ends = now + datetime.timedelta(minutes=20)
        rule = SilenceRule(starts_at=starts, ends_at=ends, matchers={}, comment="test")
        # We don't need to save it to test the method logic
        self.assertFalse(rule.is_active())

    def test_is_active_during_period(self):
        """Test is_active() returns True when now is between starts_at and ends_at."""
        now = timezone.now()
        starts = now - datetime.timedelta(minutes=5)
        ends = now + datetime.timedelta(minutes=5)
        rule = SilenceRule(starts_at=starts, ends_at=ends, matchers={}, comment="test")
        self.assertTrue(rule.is_active())

    def test_is_active_after_end(self):
        """Test is_active() returns False when now is after ends_at."""
        now = timezone.now()
        starts = now - datetime.timedelta(minutes=20)
        ends = now - datetime.timedelta(minutes=10)
        rule = SilenceRule(starts_at=starts, ends_at=ends, matchers={}, comment="test")
        self.assertFalse(rule.is_active())

    def test_is_active_at_start_time(self):
        """Test is_active() returns True when now is exactly starts_at."""
        now = timezone.now()
        # Set starts_at to now. is_active checks starts_at <= now
        rule = SilenceRule(starts_at=now, ends_at=now + datetime.timedelta(minutes=1), matchers={}, comment="test")
        self.assertTrue(rule.is_active())

    def test_is_active_at_end_time(self):
        """Test is_active() returns False when now is exactly ends_at."""
        now = timezone.now()
        # Set ends_at to now. is_active checks now < ends_at
        rule = SilenceRule(starts_at=now - datetime.timedelta(minutes=1), ends_at=now, matchers={}, comment="test")
        self.assertFalse(rule.is_active())

    def test_silence_rule_str_representation_with_user(self):
        """Test the __str__ method with a created_by user."""
        now = timezone.now()
        matchers = {"alertname": "HighCPU", "dc": "us-east-1"}
        rule = SilenceRule(
            matchers=matchers,
            starts_at=now,
            ends_at=now + datetime.timedelta(hours=1),
            comment="Test",
            created_by=self.test_user
        )
        expected_str = f'Silence rule for alertname="HighCPU", dc="us-east-1" (by {self.test_user.username})'
        self.assertEqual(str(rule), expected_str)

    def test_silence_rule_str_representation_without_user(self):
        """Test the __str__ method without a created_by user."""
        now = timezone.now()
        matchers = {"service": "database"}
        rule = SilenceRule(
            matchers=matchers,
            starts_at=now,
            ends_at=now + datetime.timedelta(hours=1),
            comment="Test",
            created_by=None
        )
        expected_str = 'Silence rule for service="database" (by System)'
        self.assertEqual(str(rule), expected_str)

    def test_silence_rule_str_representation_invalid_matchers(self):
        """Test the __str__ method when matchers are not a dict."""
        now = timezone.now()
        rule = SilenceRule(
            matchers=None, # Invalid matcher type
            starts_at=now,
            ends_at=now + datetime.timedelta(hours=1),
            comment="Test",
            created_by=self.test_user
        )
        # The __str__ method should handle this gracefully
        expected_str = f'Silence rule for Invalid Matchers (by {self.test_user.username})'
        self.assertEqual(str(rule), expected_str)


# --- New Tests for AlertGroup ---

class AlertGroupModelTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Create a user for acknowledged_by field
        cls.test_user = User.objects.create_user(username='ackuser', password='password')
        # Create a dummy AlertDocumentation if needed (adjust import if necessary)
        # try:
        #     from docs.models import AlertDocumentation
        #     cls.test_doc = AlertDocumentation.objects.create(name="Test Doc", content="Details")
        # except ImportError:
        #     cls.test_doc = None # Handle case where docs app might not exist yet

        # Create some AlertGroups for ordering tests
        cls.group1 = AlertGroup.objects.create(
            fingerprint="fp1",
            name="Alert 1",
            labels={"env": "prod", "severity": "high"},
            last_occurrence=timezone.now() - datetime.timedelta(hours=2)
        )
        import time; time.sleep(0.01) # Ensure distinct timestamps/operations
        cls.group2 = AlertGroup.objects.create(
            fingerprint="fp2",
            name="Alert 2",
            labels={"env": "staging"},
            last_occurrence=timezone.now() - datetime.timedelta(hours=1) # More recent
        )
        import time; time.sleep(0.01) # Ensure distinct timestamps/operations
        cls.group3 = AlertGroup.objects.create(
            fingerprint="fp3",
            name="Alert 3",
            labels={"app": "web"},
            last_occurrence=timezone.now() # Most recent
        )


    def test_alert_group_creation_minimal(self):
        """Test creating an AlertGroup with only required fields."""
        fingerprint = "unique_fp_minimal"
        name = "Minimal Alert"
        labels = {"alertname": "TestAlert"}

        group = AlertGroup.objects.create(
            fingerprint=fingerprint,
            name=name,
            labels=labels
        )

        self.assertIsInstance(group, AlertGroup)
        self.assertEqual(group.fingerprint, fingerprint)
        self.assertEqual(group.name, name)
        self.assertEqual(group.labels, labels)
        # Test default values
        self.assertEqual(group.severity, 'warning')
        self.assertEqual(group.current_status, 'firing')
        self.assertEqual(group.total_firing_count, 1)
        self.assertFalse(group.acknowledged)
        self.assertIsNone(group.acknowledged_by)
        self.assertIsNone(group.acknowledgement_time)
        self.assertIsNone(group.documentation)
        self.assertFalse(group.is_silenced)
        self.assertIsNone(group.silenced_until)
        self.assertIsNone(group.instance) # Default is null
        self.assertIsNotNone(group.first_occurrence)
        self.assertIsNotNone(group.last_occurrence)

    def test_alert_group_creation_full(self):
        """Test creating an AlertGroup with all fields populated."""
        fingerprint = "unique_fp_full"
        name = "Full Alert"
        labels = {"alertname": "FullTest", "instance": "server.example.com"}
        now = timezone.now()
        ack_time = now - datetime.timedelta(minutes=5)
        silence_end = now + datetime.timedelta(days=1)

        group = AlertGroup.objects.create(
            fingerprint=fingerprint,
            name=name,
            labels=labels,
            severity='critical',
            instance="server.example.com", # Explicitly set
            current_status='resolved',
            total_firing_count=5,
            acknowledged=True,
            acknowledged_by=self.test_user,
            acknowledgement_time=ack_time,
            # documentation=self.test_doc, # Uncomment if docs app exists and test_doc is created
            is_silenced=True,
            silenced_until=silence_end
        )

        self.assertEqual(group.fingerprint, fingerprint)
        self.assertEqual(group.name, name)
        self.assertEqual(group.labels, labels)
        self.assertEqual(group.severity, 'critical')
        self.assertEqual(group.instance, "server.example.com")
        self.assertEqual(group.current_status, 'resolved')
        self.assertEqual(group.total_firing_count, 5)
        self.assertTrue(group.acknowledged)
        self.assertEqual(group.acknowledged_by, self.test_user)
        self.assertEqual(group.acknowledgement_time, ack_time)
        # self.assertEqual(group.documentation, self.test_doc) # Uncomment if testing docs link
        self.assertTrue(group.is_silenced)
        self.assertEqual(group.silenced_until, silence_end)

    def test_alert_group_str_with_instance(self):
        """Test the __str__ method when instance field is populated."""
        fingerprint = "fp_with_instance"
        name = "Instance Alert"
        instance_val = "webserver-01"
        group = AlertGroup(fingerprint=fingerprint, name=name, instance=instance_val, labels={})
        expected_str = f"{name} ({instance_val})"
        self.assertEqual(str(group), expected_str)

    def test_alert_group_str_without_instance(self):
        """Test the __str__ method when instance field is null/blank."""
        fingerprint = "fp_without_instance"
        name = "No Instance Alert"
        group = AlertGroup(fingerprint=fingerprint, name=name, instance=None, labels={})
        expected_str = f"{name} ({fingerprint})"
        self.assertEqual(str(group), expected_str)

        group_blank = AlertGroup(fingerprint=fingerprint, name=name, instance="", labels={})
        expected_str_blank = f"{name} ({fingerprint})" # Should still use fingerprint if instance is blank
        self.assertEqual(str(group_blank), expected_str_blank)


    def test_alert_group_ordering(self):
        """Test that AlertGroups are ordered by last_occurrence descending."""
        groups = AlertGroup.objects.all()
        # setUpTestData created group3 (most recent), group2, group1 (least recent)
        self.assertEqual(groups[0], self.group3)
        self.assertEqual(groups[1], self.group2)
        self.assertEqual(groups[2], self.group1)


# --- New Tests for AlertInstance ---

class AlertInstanceModelTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Create a related AlertGroup
        cls.alert_group = AlertGroup.objects.create(
            fingerprint="group_for_instance_test",
            name="Instance Test Group",
            labels={"app": "test"}
        )
        # Create some AlertInstances for ordering tests
        now = timezone.now()
        cls.instance1 = AlertInstance.objects.create(
            alert_group=cls.alert_group,
            status='firing',
            started_at=now - datetime.timedelta(hours=2),
            annotations={"summary": "First instance"}
        )
        cls.instance2 = AlertInstance.objects.create(
            alert_group=cls.alert_group,
            status='resolved',
            started_at=now - datetime.timedelta(hours=1), # More recent start
            ended_at=now - datetime.timedelta(minutes=30),
            annotations={"summary": "Second instance"},
            resolution_type='normal'
        )
        cls.instance3 = AlertInstance.objects.create(
            alert_group=cls.alert_group,
            status='firing',
            started_at=now, # Most recent start
            annotations={"summary": "Third instance"},
            generator_url="http://prometheus.example.com/graph"
        )

    def test_alert_instance_creation(self):
        """Test creating an AlertInstance with required and optional fields."""
        now = timezone.now()
        start_time = now - datetime.timedelta(minutes=10)
        end_time = now - datetime.timedelta(minutes=5)
        annotations_data = {"description": "Detailed description here."}
        gen_url = "http://example.com/gen"

        instance = AlertInstance.objects.create(
            alert_group=self.alert_group,
            status='resolved',
            started_at=start_time,
            ended_at=end_time,
            annotations=annotations_data,
            generator_url=gen_url,
            resolution_type='inferred'
        )

        self.assertIsInstance(instance, AlertInstance)
        self.assertEqual(instance.alert_group, self.alert_group)
        self.assertEqual(instance.status, 'resolved')
        self.assertEqual(instance.started_at, start_time)
        self.assertEqual(instance.ended_at, end_time)
        self.assertEqual(instance.annotations, annotations_data)
        self.assertEqual(instance.generator_url, gen_url)
        self.assertEqual(instance.resolution_type, 'inferred')

    def test_alert_instance_creation_minimal(self):
        """Test creating an AlertInstance with only required fields."""
        now = timezone.now()
        start_time = now - datetime.timedelta(minutes=1)
        annotations_data = {"summary": "Minimal instance"}

        instance = AlertInstance.objects.create(
            alert_group=self.alert_group,
            status='firing',
            started_at=start_time,
            annotations=annotations_data,
        )

        self.assertIsInstance(instance, AlertInstance)
        self.assertEqual(instance.alert_group, self.alert_group)
        self.assertEqual(instance.status, 'firing')
        self.assertEqual(instance.started_at, start_time)
        self.assertEqual(instance.annotations, annotations_data)
        # Check defaults/nullable fields
        self.assertIsNone(instance.ended_at)
        self.assertIsNone(instance.generator_url)
        self.assertIsNone(instance.resolution_type)

    def test_alert_instance_str_representation(self):
        """Test the __str__ method of AlertInstance."""
        # Use instance3 created in setUpTestData
        expected_str = f"{self.alert_group.name} - {self.instance3.status} at {self.instance3.started_at}"
        self.assertEqual(str(self.instance3), expected_str)

    def test_alert_instance_ordering(self):
        """Test that AlertInstances are ordered by started_at descending."""
        instances = AlertInstance.objects.filter(alert_group=self.alert_group)
        # setUpTestData created instance3 (most recent), instance2, instance1 (least recent)
        self.assertEqual(instances[0], self.instance3)
        self.assertEqual(instances[1], self.instance2)
        self.assertEqual(instances[2], self.instance1)

    def test_alert_instance_relation_on_group_delete(self):
        """Test that AlertInstances are deleted when their AlertGroup is deleted."""
        group_to_delete = AlertGroup.objects.create(
            fingerprint="temp_group_fp",
            name="Temporary Group",
            labels={"temp": "true"}
        )
        instance_to_delete = AlertInstance.objects.create(
            alert_group=group_to_delete,
            status='firing',
            started_at=timezone.now(),
            annotations={"summary": "Instance to be deleted"}
        )
        instance_id = instance_to_delete.id

        # Ensure instance exists before deletion
        self.assertTrue(AlertInstance.objects.filter(id=instance_id).exists())

        # Delete the group
        group_to_delete.delete()

        # Ensure instance is also deleted (due to on_delete=models.CASCADE)
        self.assertFalse(AlertInstance.objects.filter(id=instance_id).exists())


# --- New Tests for AlertComment ---

class AlertCommentModelTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Create a user for the comment
        cls.comment_user = User.objects.create_user(username='commenter', password='password')
        # Create a related AlertGroup
        cls.alert_group = AlertGroup.objects.create(
            fingerprint="group_for_comment_test",
            name="Comment Test Group",
            labels={"app": "comment_test"}
        )
        # Create some AlertComments for ordering tests
        now = timezone.now()
        cls.comment1 = AlertComment.objects.create(
            alert_group=cls.alert_group,
            user=cls.comment_user,
            content="This is the first comment.",
            # created_at is auto_now_add, but we can manipulate for ordering test if needed
            # For simplicity, rely on creation order for now, assuming tests run fast enough
        )
        # Add a slight delay to ensure different created_at timestamps if needed
        import time; time.sleep(0.01) # Ensure distinct timestamps for ordering test
        cls.comment2 = AlertComment.objects.create(
            alert_group=cls.alert_group,
            user=cls.comment_user,
            content="This is the second comment, should be newer."
        )

    def test_alert_comment_creation(self):
        """Test creating an AlertComment successfully."""
        comment_text = "Investigating this alert."
        comment = AlertComment.objects.create(
            alert_group=self.alert_group,
            user=self.comment_user,
            content=comment_text
        )

        self.assertIsInstance(comment, AlertComment)
        self.assertEqual(comment.alert_group, self.alert_group)
        self.assertEqual(comment.user, self.comment_user)
        self.assertEqual(comment.content, comment_text)
        self.assertIsNotNone(comment.created_at)

    def test_alert_comment_str_representation(self):
        """Test the __str__ method of AlertComment."""
        expected_str = f"Comment by {self.comment_user.username} on {self.alert_group.name}"
        # Use comment2 created in setUpTestData
        self.assertEqual(str(self.comment2), expected_str)

    def test_alert_comment_ordering(self):
        """Test that AlertComments are ordered by created_at descending."""
        comments = AlertComment.objects.filter(alert_group=self.alert_group)
        # setUpTestData created comment1 then comment2 (most recent)
        # Compare primary keys for robust ordering check
        self.assertEqual(comments[0].pk, self.comment2.pk)
        self.assertEqual(comments[1].pk, self.comment1.pk)
        # Verify timestamps if needed (requires storing them during creation or querying)
        self.assertTrue(comments[0].created_at > comments[1].created_at)

    def test_alert_comment_relation_on_group_delete(self):
        """Test that AlertComments are deleted when their AlertGroup is deleted."""
        group_to_delete = AlertGroup.objects.create(
            fingerprint="temp_group_comment_fp",
            name="Temporary Group for Comment",
            labels={"temp": "comment"}
        )
        comment_to_delete = AlertComment.objects.create(
            alert_group=group_to_delete,
            user=self.comment_user,
            content="This comment should be deleted."
        )
        comment_id = comment_to_delete.id

        # Ensure comment exists before deletion
        self.assertTrue(AlertComment.objects.filter(id=comment_id).exists())

        # Delete the group
        group_to_delete.delete()

        # Ensure comment is also deleted (due to on_delete=models.CASCADE)
        self.assertFalse(AlertComment.objects.filter(id=comment_id).exists())

    def test_alert_comment_relation_on_user_delete(self):
        """Test that AlertComments are deleted when their User is deleted."""
        user_to_delete = User.objects.create_user(username='tempuser', password='password')
        comment_to_delete = AlertComment.objects.create(
            alert_group=self.alert_group,
            user=user_to_delete,
            content="This comment should be deleted with the user."
        )
        comment_id = comment_to_delete.id

        # Ensure comment exists before deletion
        self.assertTrue(AlertComment.objects.filter(id=comment_id).exists())

        # Delete the user
        user_to_delete.delete()

        # Ensure comment is also deleted (due to on_delete=models.CASCADE)
        self.assertFalse(AlertComment.objects.filter(id=comment_id).exists())


# --- New Tests for AlertAcknowledgementHistory ---

class AlertAcknowledgementHistoryModelTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Create a user for acknowledgements
        cls.ack_user = User.objects.create_user(username='history_ack_user', password='password')
        # Create a related AlertGroup
        cls.alert_group = AlertGroup.objects.create(
            fingerprint="group_for_ack_history_test",
            name="Ack History Test Group",
            labels={"app": "ack_history_test"}
        )
        # Create a related AlertInstance
        cls.alert_instance = AlertInstance.objects.create(
            alert_group=cls.alert_group,
            status='firing',
            started_at=timezone.now() - datetime.timedelta(hours=1),
            annotations={"summary": "Instance for Ack History"}
        )
        # Create some history entries for ordering tests
        # Create older entry first
        cls.history1 = AlertAcknowledgementHistory.objects.create(
            alert_group=cls.alert_group,
            alert_instance=cls.alert_instance,
            acknowledged_by=cls.ack_user,
            comment="First ack"
        )
        # Add a slight delay if needed to ensure distinct acknowledged_at
        import time; time.sleep(0.01) # Ensure distinct timestamps for ordering test
        cls.history2 = AlertAcknowledgementHistory.objects.create(
            alert_group=cls.alert_group,
            alert_instance=None, # Test case without instance
            acknowledged_by=cls.ack_user,
            comment="Second ack, no specific instance"
        )

    def test_ack_history_creation_full(self):
        """Test creating an AlertAcknowledgementHistory with all fields."""
        ack_comment = "Acknowledged with full details."
        history = AlertAcknowledgementHistory.objects.create(
            alert_group=self.alert_group,
            alert_instance=self.alert_instance,
            acknowledged_by=self.ack_user,
            comment=ack_comment
        )

        self.assertIsInstance(history, AlertAcknowledgementHistory)
        self.assertEqual(history.alert_group, self.alert_group)
        self.assertEqual(history.alert_instance, self.alert_instance)
        self.assertEqual(history.acknowledged_by, self.ack_user)
        self.assertEqual(history.comment, ack_comment)
        self.assertIsNotNone(history.acknowledged_at)

    def test_ack_history_creation_minimal(self):
        """Test creating an AlertAcknowledgementHistory with optional fields null."""
        history = AlertAcknowledgementHistory.objects.create(
            alert_group=self.alert_group,
            acknowledged_by=self.ack_user,
            # alert_instance is null
            # comment is null
        )

        self.assertIsInstance(history, AlertAcknowledgementHistory)
        self.assertEqual(history.alert_group, self.alert_group)
        self.assertEqual(history.acknowledged_by, self.ack_user)
        self.assertIsNone(history.alert_instance)
        self.assertIsNone(history.comment) # Should default to None/Null
        self.assertIsNotNone(history.acknowledged_at)

    def test_ack_history_str_with_instance(self):
        """Test the __str__ method when alert_instance is present."""
        # Use history1 created in setUpTestData
        expected_str = f"Acknowledgement by {self.ack_user.username} on {self.alert_group.name} (Instance ID: {self.alert_instance.id})"
        self.assertEqual(str(self.history1), expected_str)

    def test_ack_history_str_without_instance(self):
        """Test the __str__ method when alert_instance is None."""
        # Use history2 created in setUpTestData
        expected_str = f"Acknowledgement by {self.ack_user.username} on {self.alert_group.name}"
        self.assertEqual(str(self.history2), expected_str)

    def test_ack_history_ordering(self):
        """Test that AlertAcknowledgementHistory is ordered by acknowledged_at descending."""
        histories = AlertAcknowledgementHistory.objects.filter(alert_group=self.alert_group)
        # setUpTestData created history1 then history2 (most recent)
        self.assertEqual(histories[0].pk, self.history2.pk)
        self.assertEqual(histories[1].pk, self.history1.pk)
        self.assertTrue(histories[0].acknowledged_at > histories[1].acknowledged_at)

    def test_ack_history_relation_on_group_delete(self):
        """Test that AlertAcknowledgementHistory is deleted when AlertGroup is deleted (CASCADE)."""
        group_to_delete = AlertGroup.objects.create(fingerprint="temp_ack_group", name="Temp Ack Group", labels={})
        history_to_delete = AlertAcknowledgementHistory.objects.create(
            alert_group=group_to_delete,
            acknowledged_by=self.ack_user
        )
        history_id = history_to_delete.id

        self.assertTrue(AlertAcknowledgementHistory.objects.filter(id=history_id).exists())
        group_to_delete.delete()
        self.assertFalse(AlertAcknowledgementHistory.objects.filter(id=history_id).exists())

    def test_ack_history_relation_on_instance_delete(self):
        """Test that alert_instance becomes NULL when AlertInstance is deleted (SET_NULL)."""
        instance_to_delete = AlertInstance.objects.create(
            alert_group=self.alert_group, status='firing', started_at=timezone.now(), annotations={}
        )
        history_linked = AlertAcknowledgementHistory.objects.create(
            alert_group=self.alert_group,
            alert_instance=instance_to_delete,
            acknowledged_by=self.ack_user
        )
        history_id = history_linked.id

        self.assertEqual(AlertAcknowledgementHistory.objects.get(id=history_id).alert_instance, instance_to_delete)
        instance_to_delete.delete()
        # Refresh from DB
        history_linked.refresh_from_db()
        self.assertIsNone(history_linked.alert_instance)
        # Ensure the history record itself still exists
        self.assertTrue(AlertAcknowledgementHistory.objects.filter(id=history_id).exists())

    def test_ack_history_relation_on_user_delete(self):
        """Test that acknowledged_by becomes NULL when User is deleted (SET_NULL)."""
        user_to_delete = User.objects.create_user(username='temp_ack_user', password='password')
        history_linked = AlertAcknowledgementHistory.objects.create(
            alert_group=self.alert_group,
            acknowledged_by=user_to_delete
        )
        history_id = history_linked.id

        self.assertEqual(AlertAcknowledgementHistory.objects.get(id=history_id).acknowledged_by, user_to_delete)
        user_to_delete.delete()
        # Refresh from DB
        history_linked.refresh_from_db()
        self.assertIsNone(history_linked.acknowledged_by)
        # Ensure the history record itself still exists
        self.assertTrue(AlertAcknowledgementHistory.objects.filter(id=history_id).exists())


# --- New Tests for SilenceRuleForm ---

class SilenceRuleFormTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.test_user = User.objects.create_user(username='formuser', password='password')

    def _get_valid_data(self, **kwargs):
        """Helper to get valid form data, allowing overrides."""
        now = timezone.now()
        starts = now + datetime.timedelta(minutes=10)
        ends = now + datetime.timedelta(hours=1)
        data = {
            'matchers': json.dumps({"job": "testjob", "severity": "warning"}),
            'starts_at_0': starts.strftime('%Y-%m-%d'), # Date part
            'starts_at_1': starts.strftime('%H:%M:%S'), # Time part
            'ends_at_0': ends.strftime('%Y-%m-%d'),     # Date part
            'ends_at_1': ends.strftime('%H:%M:%S'),     # Time part
            'comment': "This is a valid test silence rule.",
        }
        data.update(kwargs)
        return data

    def test_silence_rule_form_valid_data(self):
        """Test SilenceRuleForm with valid data."""
        data = self._get_valid_data()
        form = SilenceRuleForm(data=data)
        self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors.as_json()}")
        # Test saving
        instance = form.save(commit=False)
        instance.created_by = self.test_user # Assign user before full save
        instance.save()
        self.assertIsInstance(instance, SilenceRule)
        self.assertEqual(instance.matchers, {"job": "testjob", "severity": "warning"})
        self.assertEqual(instance.comment, data['comment'])
        self.assertEqual(instance.created_by, self.test_user)
        # Check datetimes are close (allow for minor processing differences)
        self.assertAlmostEqual(instance.starts_at, timezone.make_aware(datetime.datetime.strptime(f"{data['starts_at_0']} {data['starts_at_1']}", '%Y-%m-%d %H:%M:%S')), delta=datetime.timedelta(seconds=1))
        self.assertAlmostEqual(instance.ends_at, timezone.make_aware(datetime.datetime.strptime(f"{data['ends_at_0']} {data['ends_at_1']}", '%Y-%m-%d %H:%M:%S')), delta=datetime.timedelta(seconds=1))


    def test_silence_rule_form_invalid_json_matchers(self):
        """Test form validation with invalid JSON in matchers."""
        data = self._get_valid_data(matchers='{"job": "testjob", severity": "warning"}') # Missing quote
        form = SilenceRuleForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('matchers', form.errors)
        # Django's default JSONField validation error seems to trigger first
        self.assertIn('Enter a valid JSON.', form.errors['matchers'])

    def test_silence_rule_form_non_object_json_matchers(self):
        """Test form validation with JSON that is not an object."""
        data = self._get_valid_data(matchers='["job", "testjob"]') # JSON array, not object
        form = SilenceRuleForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('matchers', form.errors)
        # Django's JSONField parses the list, then clean_matchers hits the 'else' block
        self.assertIn('Matchers must be provided as a JSON object.', form.errors['matchers'])

    def test_silence_rule_form_end_before_start(self):
        """Test form validation when ends_at is before starts_at."""
        now = timezone.now()
        starts = now + datetime.timedelta(hours=1)
        ends = now + datetime.timedelta(minutes=30) # Before starts
        data = self._get_valid_data(
            starts_at_0=starts.strftime('%Y-%m-%d'),
            starts_at_1=starts.strftime('%H:%M:%S'),
            ends_at_0=ends.strftime('%Y-%m-%d'),
            ends_at_1=ends.strftime('%H:%M:%S'),
        )
        form = SilenceRuleForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors) # Non-field error
        self.assertIn('End time must be after start time.', form.errors['__all__'])

    def test_silence_rule_form_end_equals_start(self):
        """Test form validation when ends_at is equal to starts_at."""
        now = timezone.now()
        the_time = now + datetime.timedelta(hours=1)
        data = self._get_valid_data(
            starts_at_0=the_time.strftime('%Y-%m-%d'),
            starts_at_1=the_time.strftime('%H:%M:%S'),
            ends_at_0=the_time.strftime('%Y-%m-%d'),
            ends_at_1=the_time.strftime('%H:%M:%S'),
        )
        form = SilenceRuleForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
        self.assertIn('End time must be after start time.', form.errors['__all__'])

    def test_silence_rule_form_missing_required_fields(self):
        """Test form validation with missing required fields."""
        required_fields = ['matchers', 'starts_at_0', 'starts_at_1', 'ends_at_0', 'ends_at_1', 'comment']
        for field in required_fields:
            data = self._get_valid_data()
            del data[field]
            form = SilenceRuleForm(data=data)
            self.assertFalse(form.is_valid(), msg=f"Form should be invalid when '{field}' is missing.")
            # Field names for SplitDateTimeField are starts_at/ends_at, others are field name itself
            if field.startswith('starts_at_') or field.startswith('ends_at_'):
                error_field_name = field.split('_')[0] + '_at' # e.g., 'starts_at'
            else:
                error_field_name = field # e.g., 'matchers', 'comment'
            self.assertIn(error_field_name, form.errors, msg=f"Error expected for missing field '{field}' (checking '{error_field_name}').")
            self.assertIn('This field is required.', form.errors[error_field_name])

    def test_silence_rule_form_initial_start_time(self):
        """Test that the starts_at field has an initial value close to now."""
        form = SilenceRuleForm()
        # initial is a callable (timezone.now), so we check the rendered widget value or bound field
        # Checking the bound field's initial value is more robust
        initial_starts_at = form.fields['starts_at'].initial()
        self.assertIsNotNone(initial_starts_at)
        # Check if it's a datetime object and close to now
        self.assertIsInstance(initial_starts_at, datetime.datetime)
        self.assertAlmostEqual(initial_starts_at, timezone.now(), delta=datetime.timedelta(seconds=5))


# --- New Tests for AlertAcknowledgementForm ---

class AlertAcknowledgementFormTests(TestCase):

    def test_ack_form_valid_comment(self):
        """Test AlertAcknowledgementForm with a valid, non-empty comment."""
        data = {'comment': 'Acknowledged, investigating the issue.'}
        form = AlertAcknowledgementForm(data=data)
        self.assertTrue(form.is_valid(), msg=f"Form should be valid with a comment. Errors: {form.errors.as_json()}")
        self.assertEqual(form.cleaned_data['comment'], data['comment'])

    def test_ack_form_missing_comment(self):
        """Test AlertAcknowledgementForm with a missing (empty) comment."""
        data = {'comment': ''}
        form = AlertAcknowledgementForm(data=data)
        self.assertFalse(form.is_valid(), msg="Form should be invalid without a comment.")
        self.assertIn('comment', form.errors)
        self.assertIn('This field is required.', form.errors['comment'])

    def test_ack_form_no_data(self):
        """Test AlertAcknowledgementForm with no data provided."""
        form = AlertAcknowledgementForm(data={})
        self.assertFalse(form.is_valid(), msg="Form should be invalid with no data.")
        self.assertIn('comment', form.errors)
        self.assertIn('This field is required.', form.errors['comment'])


# --- New Tests for AlertCommentForm ---

class AlertCommentFormTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Create a user and alert group if needed for save tests, though not strictly for validation
        cls.test_user = User.objects.create_user(username='commentformuser', password='password')
        cls.alert_group = AlertGroup.objects.create(
            fingerprint="group_for_comment_form_test",
            name="Comment Form Test Group",
            labels={"app": "comment_form_test"}
        )

    def test_comment_form_valid_data(self):
        """Test AlertCommentForm with valid, non-empty content."""
        data = {'content': 'This is a valid comment.'}
        form = AlertCommentForm(data=data)
        self.assertTrue(form.is_valid(), msg=f"Form should be valid. Errors: {form.errors.as_json()}")
        self.assertEqual(form.cleaned_data['content'], data['content'])

    def test_comment_form_empty_data(self):
        """Test AlertCommentForm with empty content (should be invalid by default)."""
        # Django's ModelForm respects the underlying model field's blank=True/False.
        # AlertComment.content is a TextField, which defaults to blank=False, required=True.
        data = {'content': ''}
        form = AlertCommentForm(data=data)
        # Default TextField is required
        self.assertFalse(form.is_valid(), msg="Form should be invalid if content is empty by default.")
        self.assertIn('content', form.errors)
        self.assertIn('This field is required.', form.errors['content'])

    def test_comment_form_no_data(self):
        """Test AlertCommentForm with no data provided."""
        form = AlertCommentForm(data={})
        self.assertFalse(form.is_valid(), msg="Form should be invalid with no data.")
        self.assertIn('content', form.errors)
        self.assertIn('This field is required.', form.errors['content'])

    def test_comment_form_save_commit_false(self):
        """Test saving the form with commit=False."""
        data = {'content': 'Saving this comment later.'}
        form = AlertCommentForm(data=data)
        self.assertTrue(form.is_valid())

        # Create an instance without saving to the database
        comment_instance = form.save(commit=False)

        self.assertIsInstance(comment_instance, AlertComment)
        self.assertEqual(comment_instance.content, data['content'])
        # Check that required foreign keys are not set yet
        self.assertIsNone(getattr(comment_instance, 'user_id', None)) # Accessing user_id directly avoids RelatedObjectDoesNotExist
        self.assertIsNone(getattr(comment_instance, 'alert_group_id', None))
        # Ensure it's not saved yet
        self.assertIsNone(comment_instance.pk)

        # Now assign required fields and save fully
        comment_instance.user = self.test_user
        comment_instance.alert_group = self.alert_group
        comment_instance.save()

        # Verify it's saved
        self.assertIsNotNone(comment_instance.pk)
        saved_comment = AlertComment.objects.get(pk=comment_instance.pk)
        self.assertEqual(saved_comment.content, data['content'])
        self.assertEqual(saved_comment.user, self.test_user)
        self.assertEqual(saved_comment.alert_group, self.alert_group)

    def test_comment_form_widget_attributes(self):
        """Test the widget attributes defined in Meta."""
        form = AlertCommentForm()
        widget = form.fields['content'].widget
        self.assertIsInstance(widget, forms.Textarea)
        self.assertEqual(widget.attrs.get('rows'), 3)
        self.assertEqual(widget.attrs.get('class'), 'form-control')


# --- New Tests for check_alert_silence Service ---

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


# --- New Tests for process_alert Service ---

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
