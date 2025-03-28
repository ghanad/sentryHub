import datetime
import json
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from django import forms

# Import models and forms from the parent 'alerts' app
from ..models import SilenceRule, AlertGroup, AlertComment
from ..forms import SilenceRuleForm, AlertAcknowledgementForm, AlertCommentForm


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
