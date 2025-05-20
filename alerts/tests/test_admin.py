from django.contrib import admin
from django.contrib.auth.models import User
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from datetime import timedelta
from unittest.mock import patch

from alerts.models import AlertGroup, AlertInstance, AlertComment, AlertAcknowledgementHistory, SilenceRule
from alerts.admin import AlertGroupAdmin, AlertInstanceAdmin, AlertCommentAdmin, AlertAcknowledgementHistoryAdmin, SilenceRuleAdmin

class AdminPageAccessibilityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            username='superadmin',
            email='superadmin@example.com',
            password='password123'
        )
        self.client.login(username='superadmin', password='password123')

        # Create one instance of each model for change views
        self.alert_group = AlertGroup.objects.create(fingerprint='fp_admin_ag', name='Admin AG Test')
        self.alert_instance = AlertInstance.objects.create(alert_group=self.alert_group, status='firing', started_at=timezone.now())
        self.alert_comment = AlertComment.objects.create(alert_group=self.alert_group, user=self.superuser, content='Admin comment test')
        self.alert_ack_history = AlertAcknowledgementHistory.objects.create(alert_group=self.alert_group, acknowledged_by=self.superuser, comment='Admin ack test')
        self.silence_rule = SilenceRule.objects.create(
            matchers={'job': 'test'}, 
            starts_at=timezone.now(), 
            ends_at=timezone.now() + timedelta(hours=1),
            created_by=self.superuser,
            comment='Admin silence rule test'
        )

    def test_admin_pages_load_successfully(self):
        models_to_test = [
            AlertGroup, AlertInstance, AlertComment, 
            AlertAcknowledgementHistory, SilenceRule
        ]
        for model_cls in models_to_test:
            app_label = model_cls._meta.app_label
            model_name = model_cls._meta.model_name
            
            # List view
            list_url = reverse(f'admin:{app_label}_{model_name}_changelist')
            response = self.client.get(list_url)
            self.assertEqual(response.status_code, 200, f"Changelist for {model_name} failed to load: {response.status_code}")

            # Add view
            add_url = reverse(f'admin:{app_label}_{model_name}_add')
            response = self.client.get(add_url)
            self.assertEqual(response.status_code, 200, f"Add view for {model_name} failed to load: {response.status_code}")

            # Change view (using the instance created in setUp)
            instance = getattr(self, model_name.lower().replace('alertgroup', 'alert_group').replace('alertinstance', 'alert_instance').replace('alertcomment', 'alert_comment').replace('alertacknowledgementhistory', 'alert_ack_history').replace('silencerule', 'silence_rule'))
            change_url = reverse(f'admin:{app_label}_{model_name}_change', args=(instance.pk,))
            response = self.client.get(change_url)
            self.assertEqual(response.status_code, 200, f"Change view for {model_name} (pk={instance.pk}) failed to load: {response.status_code}")


class AlertGroupAdminTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser('superadmin', 's@example.com', 'password')
        self.client.login(username='superadmin', password='password')
        self.alert_group_admin = AlertGroupAdmin(AlertGroup, admin.site)
        self.alert_group = AlertGroup.objects.create(fingerprint='fp_ag_admin', name='AG Admin Test')

    @override_settings(JIRA_CONFIG={'server': 'https://myjira.example.com'})
    def test_jira_issue_key_link_with_url_and_key(self):
        self.alert_group.jira_issue_key = 'PROJ-123'
        self.alert_group.save()
        
        expected_url = "https://myjira.example.com/browse/PROJ-123"
        expected_html = format_html('<a href="{}" target="_blank">{}</a>', expected_url, 'PROJ-123')
        
        # Need to pass a request object to the admin method
        # Admin methods are typically called with a request object by Django admin internals
        # For testing, we can use a mock request or just pass None if not strictly needed by the method
        # However, best practice is to simulate it if the method might use it.
        # In this case, jira_issue_key_link doesn't use the request, so obj is enough.
        self.assertEqual(self.alert_group_admin.jira_issue_key_link(self.alert_group), expected_html)

    @override_settings(JIRA_CONFIG={'server': ''}) # Jira URL is empty
    def test_jira_issue_key_link_with_key_no_url(self):
        self.alert_group.jira_issue_key = 'PROJ-456'
        self.alert_group.save()
        self.assertEqual(self.alert_group_admin.jira_issue_key_link(self.alert_group), 'PROJ-456')

    @override_settings(JIRA_CONFIG=None) # JIRA_CONFIG itself is None
    def test_jira_issue_key_link_with_key_no_jira_config(self):
        self.alert_group.jira_issue_key = 'PROJ-789'
        self.alert_group.save()
        self.assertEqual(self.alert_group_admin.jira_issue_key_link(self.alert_group), 'PROJ-789')
        
    @override_settings(JIRA_CONFIG={'server': 'https://test.com'}) # JIRA_CONFIG exists
    def test_jira_issue_key_link_no_key(self):
        self.alert_group.jira_issue_key = None
        self.alert_group.save()
        self.assertEqual(self.alert_group_admin.jira_issue_key_link(self.alert_group), '-')

        self.alert_group.jira_issue_key = ""
        self.alert_group.save()
        self.assertEqual(self.alert_group_admin.jira_issue_key_link(self.alert_group), '-')

    def test_alert_group_admin_list_display_loads(self):
        """ Test that the changelist page loads correctly with all list_display fields. """
        url = reverse('admin:alerts_alertgroup_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Check if some key list_display fields are present in the response content
        # This isn't exhaustive but checks for critical ones.
        self.assertContains(response, self.alert_group.fingerprint)
        self.assertContains(response, self.alert_group.name)
        self.assertContains(response, "jira_issue_key_link") # Check for the column header
        # Add more checks for other list_display fields if necessary

    def test_alert_group_admin_filters_and_search_load(self):
        """ Test that changelist loads with filters and search box. """
        url = reverse('admin:alerts_alertgroup_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Check for filter presence (e.g., by looking for a known filter's title)
        self.assertContains(response, "By severity") # Assuming 'severity' is in list_filter
        self.assertContains(response, "By current status") # Assuming 'current_status' is in list_filter
        # Check for search box
        self.assertContains(response, 'searchbar')

    def test_alert_group_admin_change_view_readonly_fields(self):
        """ Test that readonly fields are present in the change view. """
        url = reverse('admin:alerts_alertgroup_change', args=(self.alert_group.pk,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Check for a known readonly field's value or its "readonly" presentation
        # For example, 'fingerprint' is often readonly.
        self.assertContains(response, self.alert_group.fingerprint)
        # Django admin often wraps readonly fields in a div with class 'readonly'
        self.assertContains(response, '<div class="readonly">') 
        self.assertContains(response, 'field-fingerprint') # Check for the field's class
        self.assertContains(response, 'field-first_seen')
        self.assertContains(response, 'field-last_seen')

class SilenceRuleAdminTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser('superadmin', 's@example.com', 'password')
        self.client.login(username='superadmin', password='password')
        self.silence_rule_admin = SilenceRuleAdmin(SilenceRule, admin.site)
        self.silence_rule = SilenceRule.objects.create(
            matchers={'job': 'test_job', 'instance': 'server1'},
            starts_at=timezone.now(),
            ends_at=timezone.now() + timedelta(hours=2),
            created_by=self.superuser,
            comment='Initial comment for SilenceRuleAdmin test.'
        )

    def test_display_matchers_short_valid(self):
        matchers = {'job': 'node_exporter', 'instance': 'server1', 'severity': 'critical'}
        self.silence_rule.matchers = matchers
        expected_html = "job=node_exporter<br>instance=server1<br>severity=critical"
        self.assertEqual(self.silence_rule_admin.display_matchers_short(self.silence_rule), expected_html)

    def test_display_matchers_short_long(self):
        long_value = "a_very_long_value_that_should_definitely_be_truncated_for_display_in_admin_list"
        matchers = {'job': 'node_exporter', 'instance': long_value, 'another_key': 'short_value'}
        self.silence_rule.matchers = matchers
        
        result = self.silence_rule_admin.display_matchers_short(self.silence_rule)
        self.assertIn("job=node_exporter<br>", result)
        self.assertIn("instance=a_very_long_value_that_should_definitely_be_tr...<br>", result)
        self.assertIn("another_key=short_value", result)

    def test_display_matchers_short_non_dict(self):
        self.silence_rule.matchers = "not a dict"
        self.assertEqual(self.silence_rule_admin.display_matchers_short(self.silence_rule), "Invalid Matchers")
        
        self.silence_rule.matchers = None
        self.assertEqual(self.silence_rule_admin.display_matchers_short(self.silence_rule), "Invalid Matchers")

    def test_is_active_display(self):
        # Test active rule
        self.silence_rule.starts_at = timezone.now() - timedelta(hours=1)
        self.silence_rule.ends_at = timezone.now() + timedelta(hours=1)
        self.silence_rule.save()
        self.assertTrue(self.silence_rule_admin.is_active_display(self.silence_rule))

        # Test inactive rule (ended)
        self.silence_rule.ends_at = timezone.now() - timedelta(minutes=1)
        self.silence_rule.save()
        self.assertFalse(self.silence_rule_admin.is_active_display(self.silence_rule))

        # Test inactive rule (not yet started)
        self.silence_rule.starts_at = timezone.now() + timedelta(minutes=1)
        self.silence_rule.ends_at = timezone.now() + timedelta(hours=1)
        self.silence_rule.save()
        self.assertFalse(self.silence_rule_admin.is_active_display(self.silence_rule))
        
        # Check attributes
        self.assertTrue(getattr(self.silence_rule_admin.is_active_display, 'boolean', False))
        self.assertEqual(getattr(self.silence_rule_admin.is_active_display, 'short_description', ''), 'Active?')

    def test_comment_short(self):
        short_comment = "This is a short comment."
        self.silence_rule.comment = short_comment
        self.assertEqual(self.silence_rule_admin.comment_short(self.silence_rule), short_comment)

        long_comment = "This is a very long comment that should be truncated for display in the admin list view to prevent it from taking up too much space and making the table look cluttered."
        self.silence_rule.comment = long_comment
        expected_truncated_comment = long_comment[:50] + "..."
        self.assertEqual(self.silence_rule_admin.comment_short(self.silence_rule), expected_truncated_comment)
        self.assertEqual(getattr(self.silence_rule_admin.comment_short, 'short_description', ''), 'Comment (Short)')

    @patch('alerts.signals.check_alert_silence_for_all_alerts') # Mock to prevent actual signal processing
    def test_save_model_new_rule(self, mock_check_alerts):
        new_rule = SilenceRule(
            matchers={'new': 'rule'},
            starts_at=timezone.now(),
            ends_at=timezone.now() + timedelta(hours=1),
            comment='New rule by admin'
        )
        # Simulate request object
        mock_request = type('Request', (), {'user': self.superuser})()
        
        self.silence_rule_admin.save_model(mock_request, new_rule, form=None, change=False) # change=False for new
        
        self.assertEqual(new_rule.created_by, self.superuser)
        # Check if it was saved to DB (though save_model itself calls obj.save())
        self.assertIsNotNone(new_rule.pk)
        mock_check_alerts.assert_called_once() # Signal should be called

    @patch('alerts.signals.check_alert_silence_for_all_alerts')
    def test_save_model_update_rule(self, mock_check_alerts):
        original_creator = self.silence_rule.created_by
        self.assertNotEqual(original_creator.username, 'anotheradmin') # Ensure it's not the same as editor
        
        another_admin = User.objects.create_superuser('anotheradmin', 'a@example.com', 'password')
        mock_request = type('Request', (), {'user': another_admin})()
        
        # Simulate form data that might change other fields
        self.silence_rule.comment = "Updated comment by another admin"
        self.silence_rule_admin.save_model(mock_request, self.silence_rule, form=None, change=True) # change=True for update
        
        self.silence_rule.refresh_from_db()
        self.assertEqual(self.silence_rule.created_by, original_creator) # created_by should NOT change
        self.assertEqual(self.silence_rule.comment, "Updated comment by another admin")
        mock_check_alerts.assert_called_once()

    def test_silence_rule_admin_list_display_loads(self):
        url = reverse('admin:alerts_silencerule_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "display_matchers_short")
        self.assertContains(response, "is_active_display")
        self.assertContains(response, "comment_short")

    def test_silence_rule_admin_change_view_fieldsets_readonly(self):
        url = reverse('admin:alerts_silencerule_change', args=(self.silence_rule.pk,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Check for a readonly field
        self.assertContains(response, 'field-created_by') 
        self.assertContains(response, self.superuser.username) # Value of created_by
        # Check fieldsets structure by looking for a specific field in a fieldset
        self.assertContains(response, 'field-matchers') # Part of "Rule Definition"
        self.assertContains(response, 'field-comment') # Part of "Details"

# Basic Admin Config Tests (just to ensure list pages load with declared fields)
class OtherModelAdminsLoadTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser('superadmin', 's@example.com', 'password')
        self.client.login(username='superadmin', password='password')
        self.alert_group = AlertGroup.objects.create(fingerprint='fp_other_admin', name='Other Admin Test AG')

    def test_alert_instance_admin_loads(self):
        AlertInstance.objects.create(alert_group=self.alert_group, status='firing', started_at=timezone.now())
        url = reverse('admin:alerts_alertinstance_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_alert_comment_admin_loads(self):
        AlertComment.objects.create(alert_group=self.alert_group, user=self.superuser, content='Test comment for admin')
        url = reverse('admin:alerts_alertcomment_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_alert_ack_history_admin_loads(self):
        AlertAcknowledgementHistory.objects.create(alert_group=self.alert_group, acknowledged_by=self.superuser, comment='Test ack history for admin')
        url = reverse('admin:alerts_alertacknowledgementhistory_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

# Note: Specific field verification for OtherModelAdmins will be added later if needed,
# the primary goal for them in this subtask is general accessibility and basic config.

    def test_alert_instance_admin_config_and_load(self):
        """ Tests that AlertInstanceAdmin changelist loads and checks for key fields/filters. """
        AlertInstance.objects.create(alert_group=self.alert_group, status='firing', started_at=timezone.now())
        url = reverse('admin:alerts_alertinstance_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Check for a list_display field
        self.assertContains(response, "alert_group_link") # Custom display field
        self.assertContains(response, "status")
        # Check for a list_filter (status is a common one)
        self.assertContains(response, "By status")
        # Check for search box (implies search_fields is configured)
        self.assertContains(response, "searchbar")
        # Check for date_hierarchy (if configured, e.g., started_at)
        self.assertContains(response, "By date started_at")


    def test_alert_comment_admin_config_and_load(self):
        """ Tests that AlertCommentAdmin changelist loads and checks for key fields/filters. """
        AlertComment.objects.create(alert_group=self.alert_group, user=self.superuser, content='Test comment for admin')
        url = reverse('admin:alerts_alertcomment_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "alert_group_link")
        self.assertContains(response, "user_link")
        self.assertContains(response, "content_short")
        self.assertContains(response, "By user") # Filter
        self.assertContains(response, "searchbar")
        self.assertContains(response, "By date created_at") # date_hierarchy

    def test_alert_ack_history_admin_config_and_load(self):
        """ Tests that AlertAcknowledgementHistoryAdmin changelist loads and checks for key fields/filters. """
        AlertAcknowledgementHistory.objects.create(alert_group=self.alert_group, acknowledged_by=self.superuser, comment='Test ack history for admin')
        url = reverse('admin:alerts_alertacknowledgementhistory_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "alert_group_link")
        self.assertContains(response, "acknowledged_by_user_link")
        self.assertContains(response, "comment_short")
        self.assertContains(response, "By acknowledged by") # Filter
        self.assertContains(response, "searchbar")
        self.assertContains(response, "By date acknowledged_at") # date_hierarchy
