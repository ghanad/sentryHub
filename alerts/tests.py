import datetime
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
# Import AlertGroup, AlertInstance, AlertComment and potentially AlertDocumentation if needed for FK tests
from .models import SilenceRule, AlertGroup, AlertInstance, AlertComment, AlertAcknowledgementHistory # Added AlertAcknowledgementHistory
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
