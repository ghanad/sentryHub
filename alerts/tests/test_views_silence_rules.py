# alerts/tests/test_views_silence_rules.py

import json # Import the json module

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from unittest.mock import patch, MagicMock, ANY
from django.contrib import messages # Import messages

# Import the model and form (will be mocked)
from alerts.models import SilenceRule, AlertGroup
from alerts.forms import SilenceRuleForm

class SilenceRuleUpdateViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client.login(username='testuser', password='password')

        # Create a dummy SilenceRule instance for updating
        self.silence_rule = SilenceRule.objects.create(
            # Corrected field name from 'name' to 'comment' based on model definition
            comment="Test Rule Comment",
            matchers={"severity": "warning"},
            starts_at=timezone.now().astimezone(timezone.utc),
            ends_at=timezone.now().astimezone(timezone.utc) + timezone.timedelta(days=1),
            created_by=self.user
        )
        self.update_url = reverse('alerts:silence-rule-update', kwargs={'pk': self.silence_rule.pk})

    def test_update_view_get_authenticated(self):
        """Test GET request to update view for authenticated user."""
        response = self.client.get(self.update_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'alerts/silence_rule_form.html')
        self.assertIn('form', response.context)
        self.assertIn('silencerule', response.context)
        self.assertEqual(response.context['silencerule'], self.silence_rule)
        self.assertIn('is_update', response.context)
        self.assertTrue(response.context['is_update'])

    def test_update_view_get_unauthenticated(self):
        """Test GET request to update view for unauthenticated user."""
        self.client.logout()
        response = self.client.get(self.update_url)

        # Should redirect to login page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f'/accounts/login/?next={self.update_url}')

    @patch('alerts.views.messages')
    def test_update_view_post_valid_data(self, mock_messages):
        """Test POST request to update view with valid data."""
        updated_comment = "Updated comment"
        updated_matchers = {"severity": "critical", "env": "dev"}
        # Create naive datetimes first
        now_naive = timezone.now().replace(tzinfo=None) # Get current time, remove tzinfo
        updated_starts_at_naive = now_naive + timezone.timedelta(hours=1)
        updated_ends_at_naive = now_naive + timezone.timedelta(days=2)

        # Make them timezone-aware in the local timezone
        # This assumes Django's TIME_ZONE is set and timezone.get_current_current_timezone() works
        updated_starts_at_local = timezone.make_aware(updated_starts_at_naive, timezone.get_current_timezone())
        updated_ends_at_local = timezone.make_aware(updated_ends_at_naive, timezone.get_current_timezone())

        response = self.client.post(self.update_url, {
            'comment': updated_comment,
            'matchers': json.dumps(updated_matchers), # Form expects JSON string
            'starts_at_0': updated_starts_at_local.strftime('%Y-%m-%d'), # Date part
            'starts_at_1': updated_starts_at_local.strftime('%H:%M:%S'), # Time part
            'ends_at_0': updated_ends_at_local.strftime('%Y-%m-%d'),
            'ends_at_1': updated_ends_at_local.strftime('%H:%M:%S'),
        })

        # Refresh the instance from the database to check updates
        self.silence_rule.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('alerts:silence-rule-list'))
        self.assertEqual(self.silence_rule.comment, updated_comment)
        self.assertEqual(self.silence_rule.matchers, updated_matchers)
        # Check datetime fields with a small tolerance due to potential precision differences
        # Convert the local timezone-aware datetimes to UTC for assertion
        expected_starts_at_utc = updated_starts_at_local.astimezone(timezone.utc)
        expected_ends_at_utc = updated_ends_at_local.astimezone(timezone.utc)

        self.assertAlmostEqual(self.silence_rule.starts_at, expected_starts_at_utc, delta=timezone.timedelta(seconds=1))
        self.assertAlmostEqual(self.silence_rule.ends_at, expected_ends_at_utc, delta=timezone.timedelta(seconds=1))
        mock_messages.success.assert_called_once_with(ANY, "Silence rule updated successfully and 0 matching alerts re-evaluated.")

    @patch('alerts.views.messages')
    def test_update_view_post_invalid_data(self, mock_messages):
        """Test POST request to update view with invalid data."""
        invalid_comment = "" # Comment is required

        # Create naive datetimes for invalid scenario
        now_naive = timezone.now().replace(tzinfo=None)
        starts_at_naive = now_naive
        ends_at_naive = now_naive - timezone.timedelta(days=1) # End date before start date

        starts_at_local = timezone.make_aware(starts_at_naive, timezone.get_current_timezone())
        ends_at_local = timezone.make_aware(ends_at_naive, timezone.get_current_timezone())

        response = self.client.post(self.update_url, {
            'comment': invalid_comment,
            'matchers': json.dumps({"severity": "critical"}),
            'starts_at_0': starts_at_local.strftime('%Y-%m-%d'),
            'starts_at_1': starts_at_local.strftime('%H:%M:%S'),
            'ends_at_0': ends_at_local.strftime('%Y-%m-%d'),
            'ends_at_1': ends_at_local.strftime('%H:%M:%S'),
        })

        # The object in the database should not be updated
        original_silence_rule = SilenceRule.objects.get(pk=self.silence_rule.pk)
        self.assertEqual(original_silence_rule.comment, "Test Rule Comment") # Should not be updated

        self.assertEqual(response.status_code, 200) # Should render the form again
        self.assertTemplateUsed(response, 'alerts/silence_rule_form.html')
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())
        self.assertIn('comment', response.context['form'].errors)
        # The form error for end time before start time is a non-field error
        self.assertIn('__all__', response.context['form'].errors)
        self.assertIn('End time must be after start time.', response.context['form'].errors['__all__'])
        self.assertIn('is_update', response.context)
        self.assertTrue(response.context['is_update'])
        mock_messages.error.assert_not_called() # No success message on invalid form

    def test_update_view_post_unauthenticated(self):
        """Test POST request to update view for unauthenticated user."""
        self.client.logout()

        # Create naive datetimes for unauthenticated scenario
        now_naive = timezone.now().replace(tzinfo=None)
        starts_at_naive = now_naive
        ends_at_naive = now_naive + timezone.timedelta(days=1)

        starts_at_local = timezone.make_aware(starts_at_naive, timezone.get_current_timezone())
        ends_at_local = timezone.make_aware(ends_at_naive, timezone.get_current_timezone())

        response = self.client.post(self.update_url, {
            'comment': 'Attempted update',
            'matchers': json.dumps({"severity": "critical"}),
            'starts_at_0': starts_at_local.strftime('%Y-%m-%d'),
            'starts_at_1': starts_at_local.strftime('%H:%M:%S'),
            'ends_at_0': ends_at_local.strftime('%Y-%m-%d'),
            'ends_at_1': ends_at_local.strftime('%H:%M:%S'),
        })

        # Should redirect to login page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f'/accounts/login/?next={self.update_url}')


class SilenceRuleDeleteViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client.login(username='testuser', password='password')

        # Define a fixed ends_at for consistency in affected alerts
        self.fixed_ends_at_for_test = timezone.now().astimezone(timezone.utc) + timezone.timedelta(days=2)

        self.silence_rule = SilenceRule.objects.create(
            comment="Rule to be deleted",
            matchers={"severity": "info"},
            starts_at=timezone.now().astimezone(timezone.utc),
            ends_at=self.fixed_ends_at_for_test, # Use the fixed ends_at directly
            created_by=self.user
        )
        self.delete_url = reverse('alerts:silence-rule-delete', kwargs={'pk': self.silence_rule.pk})


    def test_delete_view_get_authenticated(self):
        """Test GET request to delete view for authenticated user."""
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'alerts/silence_rule_confirm_delete.html')
        self.assertIn('silencerule', response.context)
        self.assertEqual(response.context['silencerule'], self.silence_rule)

    def test_delete_view_get_unauthenticated(self):
        """Test GET request to delete view for unauthenticated user."""
        self.client.logout()
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f'/accounts/login/?next={self.delete_url}')

    @patch('alerts.views.messages')
    @patch('alerts.views.check_alert_silence')
    def test_delete_view_post_valid_data(self, mock_check_alert_silence, mock_messages):
        """Test POST request to delete view with valid data."""
        response = self.client.post(self.delete_url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('alerts:silence-rule-list'))
        self.assertFalse(SilenceRule.objects.filter(pk=self.silence_rule.pk).exists())
        mock_messages.success.assert_called_once()
        self.assertEqual(mock_messages.success.call_args[0][1], "Silence rule deleted successfully.")
        mock_check_alert_silence.assert_not_called() # No affected alerts initially

    @patch('alerts.views.messages')
    @patch('alerts.views.check_alert_silence')
    def test_delete_view_post_valid_data_with_affected_alerts(self, mock_check_alert_silence, mock_messages):
        """Test POST request to delete view with valid data and affected alerts."""
        # Create an alert that would be silenced by this rule
        affected_alert = AlertGroup.objects.create(
            name="Affected Alert",
            fingerprint="affected_alert_fingerprint",
            current_status="firing",
            severity="info",
            labels={"alertname": "TestAlert", "env": "production"}, # Added labels field
            is_silenced=True,
            silenced_until=self.fixed_ends_at_for_test # Use the fixed ends_at for the affected alert
        )

        response = self.client.post(self.delete_url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('alerts:silence-rule-list'))
        self.assertFalse(SilenceRule.objects.filter(pk=self.silence_rule.pk).exists())
        mock_messages.success.assert_called_once()
        self.assertEqual(mock_messages.success.call_args[0][1], f"Silence rule deleted successfully and 1 affected alerts re-evaluated.")
        mock_check_alert_silence.assert_called_once_with(affected_alert)

    def test_delete_view_post_unauthenticated(self):
        """Test POST request to delete view for unauthenticated user."""
        self.client.logout()
        response = self.client.post(self.delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f'/accounts/login/?next={self.delete_url}')
