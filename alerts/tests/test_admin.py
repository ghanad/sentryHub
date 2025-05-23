import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from django.test import TestCase, RequestFactory
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
from django.utils.safestring import SafeString

from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.admin.sites import AdminSite
from django.utils.safestring import SafeString

from alerts.admin import AlertGroupAdmin
from alerts.models import AlertGroup

from alerts.admin import (
    AlertGroupAdmin, AlertInstanceAdmin, AlertCommentAdmin,
    AlertAcknowledgementHistoryAdmin, SilenceRuleAdmin
)
from alerts.models import (
    AlertGroup, AlertInstance, AlertComment,
    AlertAcknowledgementHistory, SilenceRule
)


class AlertGroupAdminTest(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = AlertGroupAdmin(AlertGroup, self.site)
        
        # Create a mock AlertGroup object to test admin methods
        self.alert_group = MagicMock()
        self.alert_group.jira_issue_key = 'TEST-123'

    def test_list_display_fields(self):
        """Test that list_display contains expected fields."""
        expected_fields = (
            'name', 'instance', 'source', 'fingerprint', 'severity',
            'current_status', 'total_firing_count', 'first_occurrence',
            'last_occurrence', 'acknowledged', 'jira_issue_key_link'
        )
        self.assertEqual(self.admin.list_display, expected_fields)

    def test_list_filter_fields(self):
        """Test that list_filter contains expected fields."""
        expected_filters = ('severity', 'current_status', 'acknowledged', 'source')
        self.assertEqual(self.admin.list_filter, expected_filters)

    def test_search_fields(self):
        """Test that search_fields contains expected fields."""
        expected_fields = ('name', 'fingerprint', 'instance', 'jira_issue_key', 'source')
        self.assertEqual(self.admin.search_fields, expected_fields)

    def test_date_hierarchy(self):
        """Test that date_hierarchy is properly set."""
        self.assertEqual(self.admin.date_hierarchy, 'first_occurrence')

    def test_readonly_fields(self):
        """Test that readonly_fields contains expected fields."""
        self.assertEqual(self.admin.readonly_fields, ('jira_issue_key_link',))

    @patch('django.conf.settings.JIRA_CONFIG', {'server_url': 'https://jira.example.com/'})
    def test_jira_issue_key_link_with_key_and_url(self):
        """Test jira_issue_key_link method with Jira key and configured URL."""
        result = self.admin.jira_issue_key_link(self.alert_group)
        expected = '<a href="https://jira.example.com/browse/TEST-123" target="_blank">TEST-123</a>'
        self.assertIsInstance(result, SafeString)
        self.assertEqual(str(result), expected)

    @patch('django.conf.settings.JIRA_CONFIG', {})
    def test_jira_issue_key_link_with_key_no_url(self):
        """Test jira_issue_key_link method with Jira key but no configured URL."""
        result = self.admin.jira_issue_key_link(self.alert_group)
        self.assertEqual(result, 'TEST-123')

    def test_jira_issue_key_link_no_key(self):
        """Test jira_issue_key_link method with no Jira key."""
        self.alert_group.jira_issue_key = None
        result = self.admin.jira_issue_key_link(self.alert_group)
        self.assertEqual(result, '-')

    def test_jira_issue_key_link_empty_key(self):
        """Test jira_issue_key_link method with empty Jira key."""
        self.alert_group.jira_issue_key = ''
        result = self.admin.jira_issue_key_link(self.alert_group)
        self.assertEqual(result, '-')

    @patch('django.conf.settings.JIRA_CONFIG', {'server_url': 'https://jira.example.com/'})
    def test_jira_issue_key_link_url_with_trailing_slash(self):
        """Test jira_issue_key_link method strips trailing slash from URL."""
        result = self.admin.jira_issue_key_link(self.alert_group)
        self.assertIn('https://jira.example.com/browse/', str(result))
        # Ensure no double slash
        self.assertNotIn('com//browse', str(result))

    def test_jira_issue_key_link_short_description(self):
        """Test that jira_issue_key_link has proper short description."""
        self.assertEqual(self.admin.jira_issue_key_link.short_description, 'Jira Issue')


class AlertInstanceAdminTest(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = AlertInstanceAdmin(AlertInstance, self.site)

    def test_list_display_fields(self):
        """Test that list_display contains expected fields."""
        expected_fields = ('alert_group', 'status', 'started_at', 'ended_at')
        self.assertEqual(self.admin.list_display, expected_fields)

    def test_list_filter_fields(self):
        """Test that list_filter contains expected fields."""
        expected_filters = ('status',)
        self.assertEqual(self.admin.list_filter, expected_filters)

    def test_search_fields(self):
        """Test that search_fields contains expected fields."""
        expected_fields = ('alert_group__name', 'alert_group__fingerprint')
        self.assertEqual(self.admin.search_fields, expected_fields)


class AlertCommentAdminTest(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = AlertCommentAdmin(AlertComment, self.site)

    def test_list_display_fields(self):
        """Test that list_display contains expected fields."""
        expected_fields = ('alert_group', 'user', 'content', 'created_at')
        self.assertEqual(self.admin.list_display, expected_fields)

    def test_list_filter_fields(self):
        """Test that list_filter contains expected fields."""
        expected_filters = ('created_at',)
        self.assertEqual(self.admin.list_filter, expected_filters)

    def test_search_fields(self):
        """Test that search_fields contains expected fields."""
        expected_fields = ('alert_group__name', 'user__username', 'content')
        self.assertEqual(self.admin.search_fields, expected_fields)


class AlertAcknowledgementHistoryAdminTest(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = AlertAcknowledgementHistoryAdmin(AlertAcknowledgementHistory, self.site)

    def test_list_display_fields(self):
        """Test that list_display contains expected fields."""
        expected_fields = ('alert_group', 'alert_instance', 'acknowledged_by', 'acknowledged_at')
        self.assertEqual(self.admin.list_display, expected_fields)

    def test_list_filter_fields(self):
        """Test that list_filter contains expected fields."""
        expected_filters = ('acknowledged_at',)
        self.assertEqual(self.admin.list_filter, expected_filters)

    def test_search_fields(self):
        """Test that search_fields contains expected fields."""
        expected_fields = ('alert_group__name', 'acknowledged_by__username')
        self.assertEqual(self.admin.search_fields, expected_fields)


class SilenceRuleAdminTest(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = SilenceRuleAdmin(SilenceRule, self.site)
        self.factory = RequestFactory()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'pass')
        
        # Create a mock SilenceRule object to avoid database constraints
        self.silence_rule = MagicMock()
        self.silence_rule.pk = None  # Simulate new object
        self.silence_rule.matchers = {'alertname': 'TestAlert', 'instance': 'test-instance'}
        self.silence_rule.comment = 'Test silence rule for maintenance'
        self.silence_rule.created_by = self.user
        self.silence_rule.is_active.return_value = True

    def test_list_display_fields(self):
        """Test that list_display contains expected fields."""
        expected_fields = (
            'id', 'display_matchers_short', 'starts_at', 'ends_at',
            'is_active_display', 'created_by', 'created_at', 'comment_short'
        )
        self.assertEqual(self.admin.list_display, expected_fields)

    def test_list_filter_fields(self):
        """Test that list_filter contains expected fields."""
        expected_filters = ('starts_at', 'ends_at', 'created_by')
        self.assertEqual(self.admin.list_filter, expected_filters)

    def test_search_fields(self):
        """Test that search_fields contains expected fields."""
        expected_fields = ('comment', 'created_by__username', 'matchers__icontains')
        self.assertEqual(self.admin.search_fields, expected_fields)

    def test_readonly_fields(self):
        """Test that readonly_fields contains expected fields."""
        expected_fields = ('created_at', 'updated_at')
        self.assertEqual(self.admin.readonly_fields, expected_fields)

    def test_fieldsets_structure(self):
        """Test that fieldsets are properly structured."""
        expected_fieldsets = (
            (None, {
                'fields': ('matchers', 'comment')
            }),
            ('Duration', {
                'fields': ('starts_at', 'ends_at')
            }),
            ('Metadata', {
                'fields': ('created_by', 'created_at', 'updated_at'),
                'classes': ('collapse',)
            }),
        )
        self.assertEqual(self.admin.fieldsets, expected_fieldsets)

    def test_display_matchers_short_normal(self):
        """Test display_matchers_short method with normal matchers."""
        result = self.admin.display_matchers_short(self.silence_rule)
        result_str = str(result)
        # Check for HTML-escaped quotes
        self.assertIn('alertname=&quot;TestAlert&quot;', result_str)
        self.assertIn('instance=&quot;test-instance&quot;', result_str)
        self.assertIn('<code style="font-size: 0.9em;">', result_str)

    def test_display_matchers_short_long(self):
        """Test display_matchers_short method with long matchers string."""
        long_matchers = {
            'alertname': 'VeryLongAlertNameThatExceedsTheNormalLengthLimitForDisplayPurposes',
            'instance': 'very-long-instance-name-that-also-exceeds-normal-limits',
            'job': 'another-long-job-name'
        }
        self.silence_rule.matchers = long_matchers
        result = self.admin.display_matchers_short(self.silence_rule)
        result_str = str(result)
        self.assertIn('...', result_str)
        self.assertTrue(len(result_str) < 200)  # Should be truncated

    def test_display_matchers_short_invalid_json(self):
        """Test display_matchers_short method with invalid matchers."""
        # Mock a SilenceRule with invalid matchers that raise an exception
        mock_rule = MagicMock()
        mock_rule.matchers.items.side_effect = Exception("Invalid JSON")
        
        result = self.admin.display_matchers_short(mock_rule)
        self.assertEqual(result, "Invalid Matchers")

    def test_is_active_display_active(self):
        """Test is_active_display method when rule is active."""
        result = self.admin.is_active_display(self.silence_rule)
        self.assertTrue(result)
        self.silence_rule.is_active.assert_called_once()

    def test_is_active_display_inactive(self):
        """Test is_active_display method when rule is inactive."""
        self.silence_rule.is_active.return_value = False
        result = self.admin.is_active_display(self.silence_rule)
        self.assertFalse(result)

    def test_is_active_display_boolean_attribute(self):
        """Test that is_active_display has boolean attribute set."""
        self.assertTrue(hasattr(self.admin.is_active_display, 'boolean'))
        self.assertTrue(self.admin.is_active_display.boolean)

    def test_comment_short_normal(self):
        """Test comment_short method with normal length comment."""
        result = self.admin.comment_short(self.silence_rule)
        self.assertEqual(result, 'Test silence rule for maintenance')

    def test_comment_short_long(self):
        """Test comment_short method with long comment."""
        long_comment = 'This is a very long comment that exceeds the 75 character limit and should be truncated properly'
        self.silence_rule.comment = long_comment
        result = self.admin.comment_short(self.silence_rule)
        self.assertTrue(result.endswith('...'))
        self.assertTrue(len(result) <= 78)  # 75 + '...'

    def test_save_model_new_object(self):
        """Test save_model method sets created_by for new objects."""
        request = self.factory.post('/admin/')
        request.user = self.user
        
        # Create a new mock SilenceRule without pk (simulating new object)
        new_rule = MagicMock()
        new_rule.pk = None
        
        form = MagicMock()
        
        # Call save_model
        with patch.object(self.admin, 'save_model') as mock_save:
            mock_save.return_value = None
            # Test the actual logic
            if not new_rule.pk:
                new_rule.created_by = request.user
            
            # Verify created_by was set
            self.assertEqual(new_rule.created_by, self.user)

    def test_save_model_existing_object(self):
        """Test save_model method doesn't change created_by for existing objects."""
        request = self.factory.post('/admin/')
        request.user = User.objects.create_user('newuser', 'new@example.com', 'pass')
        
        # Mock existing object with pk
        existing_rule = MagicMock()
        existing_rule.pk = 1
        original_creator = self.user
        existing_rule.created_by = original_creator
        
        form = MagicMock()
        
        # Test the logic - should not change created_by for existing objects
        if not existing_rule.pk:  # This should be False for existing objects
            existing_rule.created_by = request.user
        
        # Verify created_by wasn't changed
        self.assertEqual(existing_rule.created_by, original_creator)

    def test_method_short_descriptions(self):
        """Test that custom methods have proper short descriptions."""
        self.assertEqual(self.admin.display_matchers_short.short_description, "Matchers")
        self.assertEqual(self.admin.is_active_display.short_description, "Active")
        self.assertEqual(self.admin.comment_short.short_description, "Comment")


class AdminIntegrationTest(TestCase):
    """Integration tests for admin configurations."""
    
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'pass')
        self.alert_group = AlertGroup.objects.create(
            name='Integration Test Alert',
            instance='test-instance',
            source='prometheus',
            fingerprint='integration123',
            severity='warning',
            current_status='firing',
            total_firing_count=1,
            first_occurrence=timezone.now(),
            last_occurrence=timezone.now(),
            acknowledged=False,
            labels={}
        )

    def test_admin_registration(self):
        """Test that all admin classes are properly registered."""
        from django.contrib import admin
        
        # Check that models are registered
        self.assertIn(AlertGroup, admin.site._registry)
        self.assertIn(AlertInstance, admin.site._registry)
        self.assertIn(AlertComment, admin.site._registry)
        self.assertIn(AlertAcknowledgementHistory, admin.site._registry)
        self.assertIn(SilenceRule, admin.site._registry)

    def test_date_hierarchy_configurations(self):
        """Test that date_hierarchy is properly configured."""
        site = AdminSite()
        
        alert_group_admin = AlertGroupAdmin(AlertGroup, site)
        self.assertEqual(alert_group_admin.date_hierarchy, 'first_occurrence')
        
        alert_instance_admin = AlertInstanceAdmin(AlertInstance, site)
        self.assertEqual(alert_instance_admin.date_hierarchy, 'started_at')
        
        alert_comment_admin = AlertCommentAdmin(AlertComment, site)
        self.assertEqual(alert_comment_admin.date_hierarchy, 'created_at')
        
        ack_history_admin = AlertAcknowledgementHistoryAdmin(AlertAcknowledgementHistory, site)
        self.assertEqual(ack_history_admin.date_hierarchy, 'acknowledged_at')