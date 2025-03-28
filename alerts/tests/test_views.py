import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch # Added for mocking

from alerts.models import AlertGroup, AlertInstance, AlertComment, AlertAcknowledgementHistory
from docs.models import AlertDocumentation, DocumentationAlertGroup # Added docs models

# === AlertListView Tests ===

class AlertListViewTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Create a user for login
        cls.username = 'testuser'
        cls.password = 'testpassword'
        cls.user = User.objects.create_user(username=cls.username, password=cls.password)

        # Create some AlertGroup instances first
        now = timezone.now()
        cls.alert1 = AlertGroup.objects.create(name="High CPU Usage", fingerprint="fp1", severity="critical", current_status="firing", instance="server1.example.com", acknowledged=False, is_silenced=False, labels={"env": "prod", "service": "api"})
        cls.alert2 = AlertGroup.objects.create(name="Disk Space Low", fingerprint="fp2", severity="warning", current_status="firing", instance="server2.example.com", acknowledged=True, is_silenced=False, labels={"env": "staging", "service": "db"})
        cls.alert3 = AlertGroup.objects.create(name="Network Latency", fingerprint="fp3", severity="warning", current_status="resolved", instance="server1.example.com", acknowledged=False, is_silenced=True, silenced_until=now + timedelta(days=1), labels={"env": "prod", "service": "web"})
        cls.alert4 = AlertGroup.objects.create(name="High CPU Usage", fingerprint="fp4", severity="critical", current_status="firing", instance="server3.example.com", acknowledged=False, is_silenced=False, labels={"env": "prod", "service": "worker"})

        # Manually set last_occurrence to desired values using update to bypass auto_now=True
        cls.alert1_time = now - timedelta(hours=1)
        cls.alert2_time = now - timedelta(hours=2)
        cls.alert3_time = now - timedelta(hours=3)
        cls.alert4_time = now - timedelta(minutes=30) # Most recent

        AlertGroup.objects.filter(pk=cls.alert1.pk).update(last_occurrence=cls.alert1_time)
        AlertGroup.objects.filter(pk=cls.alert2.pk).update(last_occurrence=cls.alert2_time)
        AlertGroup.objects.filter(pk=cls.alert3.pk).update(last_occurrence=cls.alert3_time)
        AlertGroup.objects.filter(pk=cls.alert4.pk).update(last_occurrence=cls.alert4_time)

        # Refresh objects from DB to get the updated timestamps
        cls.alert1.refresh_from_db()
        cls.alert2.refresh_from_db()
        cls.alert3.refresh_from_db()
        cls.alert4.refresh_from_db()

        cls.client = Client()
        cls.url = reverse('alerts:alert-list')

    def test_login_required(self):
        """Test that unauthenticated users are redirected to login."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        # Check if the redirect URL starts with the LOGIN_URL from settings
        from django.conf import settings
        self.assertTrue(response.url.startswith(settings.LOGIN_URL))

    def test_authenticated_get_success(self):
        """Test successful GET request for authenticated users."""
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'alerts/alert_list.html')
        self.assertIn('alerts', response.context)
        self.assertEqual(len(response.context['alerts']), 4) # All alerts initially

    def test_ordering(self):
        """Test that alerts are ordered by last_occurrence descending."""
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.url)
        alerts_in_context = list(response.context['alerts'])
        self.assertEqual(alerts_in_context[0], self.alert4) # Most recent
        self.assertEqual(alerts_in_context[1], self.alert1)
        self.assertEqual(alerts_in_context[2], self.alert2)
        self.assertEqual(alerts_in_context[3], self.alert3) # Least recent

    # --- Filtering Tests ---

    def test_filter_by_status_firing(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.url, {'status': 'firing'})
        self.assertEqual(response.status_code, 200)
        alerts_in_context = list(response.context['alerts'])
        self.assertEqual(len(alerts_in_context), 3)
        self.assertIn(self.alert1, alerts_in_context)
        self.assertIn(self.alert2, alerts_in_context)
        self.assertIn(self.alert4, alerts_in_context)
        self.assertNotIn(self.alert3, alerts_in_context)
        self.assertEqual(response.context['status'], 'firing')

    def test_filter_by_status_resolved(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.url, {'status': 'resolved'})
        self.assertEqual(response.status_code, 200)
        alerts_in_context = list(response.context['alerts'])
        self.assertEqual(len(alerts_in_context), 1)
        self.assertIn(self.alert3, alerts_in_context)
        self.assertNotIn(self.alert1, alerts_in_context)
        self.assertEqual(response.context['status'], 'resolved')

    def test_filter_by_severity_critical(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.url, {'severity': 'critical'})
        self.assertEqual(response.status_code, 200)
        alerts_in_context = list(response.context['alerts'])
        self.assertEqual(len(alerts_in_context), 2)
        self.assertIn(self.alert1, alerts_in_context)
        self.assertIn(self.alert4, alerts_in_context)
        self.assertEqual(response.context['severity'], 'critical')

    def test_filter_by_instance(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.url, {'instance': 'server1.example.com'})
        self.assertEqual(response.status_code, 200)
        alerts_in_context = list(response.context['alerts'])
        self.assertEqual(len(alerts_in_context), 2)
        self.assertIn(self.alert1, alerts_in_context)
        self.assertIn(self.alert3, alerts_in_context)
        self.assertEqual(response.context['instance'], 'server1.example.com')

    def test_filter_by_acknowledged_true(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.url, {'acknowledged': 'true'})
        self.assertEqual(response.status_code, 200)
        alerts_in_context = list(response.context['alerts'])
        self.assertEqual(len(alerts_in_context), 1)
        self.assertIn(self.alert2, alerts_in_context)
        self.assertEqual(response.context['acknowledged'], 'true')

    def test_filter_by_acknowledged_false(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.url, {'acknowledged': 'false'})
        self.assertEqual(response.status_code, 200)
        alerts_in_context = list(response.context['alerts'])
        self.assertEqual(len(alerts_in_context), 3)
        self.assertIn(self.alert1, alerts_in_context)
        self.assertIn(self.alert3, alerts_in_context)
        self.assertIn(self.alert4, alerts_in_context)
        self.assertEqual(response.context['acknowledged'], 'false')

    def test_filter_by_silenced_yes(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.url, {'silenced': 'yes'})
        self.assertEqual(response.status_code, 200)
        alerts_in_context = list(response.context['alerts'])
        self.assertEqual(len(alerts_in_context), 1)
        self.assertIn(self.alert3, alerts_in_context)
        self.assertEqual(response.context['silenced_filter'], 'yes')

    def test_filter_by_silenced_no(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.url, {'silenced': 'no'})
        self.assertEqual(response.status_code, 200)
        alerts_in_context = list(response.context['alerts'])
        self.assertEqual(len(alerts_in_context), 3)
        self.assertIn(self.alert1, alerts_in_context)
        self.assertIn(self.alert2, alerts_in_context)
        self.assertIn(self.alert4, alerts_in_context)
        self.assertEqual(response.context['silenced_filter'], 'no')

    def test_filter_by_search_name(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.url, {'search': 'High CPU'})
        self.assertEqual(response.status_code, 200)
        alerts_in_context = list(response.context['alerts'])
        self.assertEqual(len(alerts_in_context), 2)
        self.assertIn(self.alert1, alerts_in_context)
        self.assertIn(self.alert4, alerts_in_context)
        self.assertEqual(response.context['search'], 'High CPU')

    def test_filter_by_search_fingerprint(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.url, {'search': 'fp2'})
        self.assertEqual(response.status_code, 200)
        alerts_in_context = list(response.context['alerts'])
        self.assertEqual(len(alerts_in_context), 1)
        self.assertIn(self.alert2, alerts_in_context)
        self.assertEqual(response.context['search'], 'fp2')

    def test_filter_by_search_instance(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.url, {'search': 'server1'})
        self.assertEqual(response.status_code, 200)
        alerts_in_context = list(response.context['alerts'])
        self.assertEqual(len(alerts_in_context), 2)
        self.assertIn(self.alert1, alerts_in_context)
        self.assertIn(self.alert3, alerts_in_context)
        self.assertEqual(response.context['search'], 'server1')

    def test_filter_combined(self):
        """Test combining multiple filters."""
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.url, {
            'status': 'firing',
            'severity': 'critical',
            'acknowledged': 'false',
            'search': 'server' # Matches alert1 and alert4 instances
        })
        self.assertEqual(response.status_code, 200)
        alerts_in_context = list(response.context['alerts'])
        # alert1: firing, critical, not ack, server1
        # alert4: firing, critical, not ack, server3
        self.assertEqual(len(alerts_in_context), 2)
        self.assertIn(self.alert1, alerts_in_context)
        self.assertIn(self.alert4, alerts_in_context)
        self.assertEqual(response.context['status'], 'firing')
        self.assertEqual(response.context['severity'], 'critical')
        self.assertEqual(response.context['acknowledged'], 'false')
        self.assertEqual(response.context['search'], 'server')

    # --- Pagination Tests ---

    def test_pagination_enabled(self):
        """Test that pagination is active when exceeding paginate_by."""
        self.client.login(username=self.username, password=self.password)
        # Create more alerts to exceed paginate_by=20 (currently 4)
        for i in range(5, 22):
            AlertGroup.objects.create(
                name=f"Alert {i}",
                fingerprint=f"fp{i}",
                severity="info",
                current_status="firing",
                instance=f"server{i}.example.com",
                last_occurrence=timezone.now() - timedelta(minutes=i*5),
                labels={} # Add default labels
            )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_paginated'])
        self.assertEqual(len(response.context['alerts']), 20) # Default paginate_by
        self.assertEqual(response.context['paginator'].num_pages, 2)

        # Test accessing page 2
        response_page2 = self.client.get(self.url, {'page': 2})
        self.assertEqual(response_page2.status_code, 200)
        self.assertEqual(len(response_page2.context['alerts']), 1) # 21 total alerts - 20 on page 1 = 1 left

    def test_pagination_invalid_page(self):
        """Test accessing an invalid page number defaults correctly."""
        self.client.login(username=self.username, password=self.password)
        # Create enough alerts for multiple pages
        for i in range(5, 25):
            AlertGroup.objects.create(
                name=f"Alert {i}",
                fingerprint=f"fp{i}",
                last_occurrence=timezone.now(),
                labels={} # Add default labels
            )

        # Test invalid page (zero) - should default to page 1
        response_zero = self.client.get(self.url, {'page': 0})
        self.assertEqual(response_zero.status_code, 200)
        self.assertEqual(response_zero.context['page_obj'].number, 1)

        # Test page out of range (too high)
        response_high = self.client.get(self.url, {'page': 99})
        self.assertEqual(response_high.status_code, 200)
        # Should go to the last page (page 2 in this case: 4 initial + 20 new = 24 total)
        self.assertEqual(response_high.context['page_obj'].number, 2)

    # --- Context Data Tests ---

    def test_context_filter_params(self):
        """Test that filter parameters are correctly passed to context."""
        self.client.login(username=self.username, password=self.password)
        params = {
            'status': 'firing',
            'severity': 'warning',
            'instance': 'server2',
            'acknowledged': 'true',
            'silenced': 'no',
            'search': 'Disk'
        }
        response = self.client.get(self.url, params)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['status'], 'firing')
        self.assertEqual(response.context['severity'], 'warning')
        self.assertEqual(response.context['instance'], 'server2')
        self.assertEqual(response.context['acknowledged'], 'true')
        self.assertEqual(response.context['silenced_filter'], 'no')
        self.assertEqual(response.context['search'], 'Disk')

    def test_context_counts(self):
        """Test that context counts are calculated correctly for the current page."""
        self.client.login(username=self.username, password=self.password)
        # Initial page has alert1 (firing, critical), alert2 (firing, warning, ack),
        # alert3 (resolved, warning, silenced), alert4 (firing, critical)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        # These counts are now for the current page only due to view changes
        self.assertEqual(response.context['firing_count'], 3) # alert1, alert2, alert4
        self.assertEqual(response.context['critical_count'], 2) # alert1, alert4
        self.assertEqual(response.context['acknowledged_count'], 1) # alert2
        # Check total counts added in get_context_data
        self.assertEqual(response.context['total_firing_count'], 3)
        self.assertEqual(response.context['total_critical_count'], 2)
        self.assertEqual(response.context['total_acknowledged_count'], 1)


        # Test counts with filtering (only alert1 should match)
        response_filtered = self.client.get(self.url, {'severity': 'critical', 'instance': 'server1'})
        self.assertEqual(response_filtered.status_code, 200)
        self.assertEqual(len(response_filtered.context['alerts']), 1)
        self.assertEqual(response_filtered.context['firing_count'], 1) # alert1 is firing
        self.assertEqual(response_filtered.context['critical_count'], 1) # alert1 is critical
        self.assertEqual(response_filtered.context['acknowledged_count'], 0) # alert1 is not ack
        # Check total counts with filter
        self.assertEqual(response_filtered.context['total_firing_count'], 1)
        self.assertEqual(response_filtered.context['total_critical_count'], 1)
        self.assertEqual(response_filtered.context['total_acknowledged_count'], 0)


# === AlertDetailView Tests ===

class AlertDetailViewTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.username = 'testuser'
        cls.password = 'testpassword'
        cls.user = User.objects.create_user(username=cls.username, password=cls.password)

        cls.alert_group = AlertGroup.objects.create(
            name="Detailed Alert",
            fingerprint="detail-fp1",
            severity="warning",
            current_status="firing",
            instance="detail-server.example.com",
            labels={"service": "detail-service"}
        )
        cls.url = reverse('alerts:alert-detail', kwargs={'fingerprint': cls.alert_group.fingerprint})
        cls.invalid_url = reverse('alerts:alert-detail', kwargs={'fingerprint': 'nonexistent-fp'})

        # Create related objects
        now = timezone.now()
        for i in range(15): # Create 15 instances for pagination test
            AlertInstance.objects.create(
                alert_group=cls.alert_group,
                status='firing' if i < 12 else 'resolved', # Mix statuses
                started_at=now - timedelta(hours=i+1),
                ended_at=now - timedelta(hours=i) if i >= 12 else None,
                annotations={'summary': f'Instance {i+1}'}
            )

        for i in range(12): # Create 12 comments for pagination test
            AlertComment.objects.create(
                alert_group=cls.alert_group,
                user=cls.user,
                content=f"This is comment number {i+1}",
                created_at=now - timedelta(minutes=i*10)
            )

        AlertAcknowledgementHistory.objects.create(
            alert_group=cls.alert_group,
            acknowledged_by=cls.user,
            comment="Initial acknowledgement"
        )

        cls.documentation = AlertDocumentation.objects.create(
            title="Troubleshooting Detailed Alert", # Use 'title' instead of 'name'
            description="Steps to fix Detailed Alert" # Remove 'labels'
            # created_by can be added if needed for other tests
        )
        DocumentationAlertGroup.objects.create(
            documentation=cls.documentation,
            alert_group=cls.alert_group
        )

        cls.client = Client()

    def test_login_required(self):
        """Test detail view requires login."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        from django.conf import settings
        self.assertTrue(response.url.startswith(settings.LOGIN_URL))

    def test_get_success_valid_fingerprint(self):
        """Test GET request with valid fingerprint."""
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'alerts/alert_detail.html')
        self.assertEqual(response.context['alert'], self.alert_group)

    def test_get_not_found_invalid_fingerprint(self):
        """Test GET request with invalid fingerprint returns 404."""
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.invalid_url)
        self.assertEqual(response.status_code, 404)

    def test_context_data(self):
        """Test context data is correctly populated."""
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        context = response.context

        self.assertEqual(context['alert'], self.alert_group)
        self.assertIn('acknowledge_form', context)
        self.assertIn('comment_form', context)
        self.assertIn('instances', context)
        self.assertIn('acknowledgement_history', context)
        self.assertIn('comments', context)
        self.assertIn('linked_documentation', context)
        self.assertEqual(context['active_tab'], 'details') # Default tab

        # Check specific context items
        self.assertEqual(context['linked_documentation'].count(), 1)
        self.assertEqual(context['linked_documentation'].first().documentation, self.documentation)
        self.assertEqual(context['acknowledgement_history'].count(), 1)

    def test_context_active_tab(self):
        """Test active_tab context variable from GET parameter."""
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.url, {'tab': 'history'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['active_tab'], 'history')

    def test_instance_pagination(self):
        """Test pagination for alert instances."""
        self.client.login(username=self.username, password=self.password)
        # Page 1
        response_p1 = self.client.get(self.url)
        self.assertEqual(response_p1.status_code, 200)
        self.assertEqual(len(response_p1.context['instances']), 10) # Default 10 per page
        self.assertTrue(response_p1.context['instances'].has_next())

        # Page 2
        response_p2 = self.client.get(self.url, {'page': 2})
        self.assertEqual(response_p2.status_code, 200)
        self.assertEqual(len(response_p2.context['instances']), 5) # 15 total instances
        self.assertFalse(response_p2.context['instances'].has_next())

        # Invalid page defaults to 1
        response_invalid = self.client.get(self.url, {'page': 'abc'})
        self.assertEqual(response_invalid.status_code, 200)
        self.assertEqual(response_invalid.context['instances'].number, 1)

        # Out of range defaults to last page
        response_high = self.client.get(self.url, {'page': 99})
        self.assertEqual(response_high.status_code, 200)
        self.assertEqual(response_high.context['instances'].number, 2) # Should be last page (2)

    def test_comment_pagination(self):
        """Test pagination for comments."""
        self.client.login(username=self.username, password=self.password)
        # Page 1
        response_p1 = self.client.get(self.url)
        self.assertEqual(response_p1.status_code, 200)
        self.assertEqual(len(response_p1.context['comments']), 10) # Default 10 per page
        self.assertTrue(response_p1.context['comments'].has_next())

        # Page 2
        response_p2 = self.client.get(self.url, {'comments_page': 2})
        self.assertEqual(response_p2.status_code, 200)
        self.assertEqual(len(response_p2.context['comments']), 2) # 12 total comments
        self.assertFalse(response_p2.context['comments'].has_next())

        # Invalid page defaults to 1
        response_invalid = self.client.get(self.url, {'comments_page': 'abc'})
        self.assertEqual(response_invalid.status_code, 200)
        self.assertEqual(response_invalid.context['comments'].number, 1)

        # Out of range defaults to last page
        response_high = self.client.get(self.url, {'comments_page': 99})
        self.assertEqual(response_high.status_code, 200)
        self.assertEqual(response_high.context['comments'].number, 2) # Should be last page (2)

    # --- POST Tests ---

    @patch('alerts.views.acknowledge_alert') # Mock the service call
    def test_post_acknowledge_valid(self, mock_acknowledge_alert):
        """Test valid POST request for acknowledgement."""
        self.client.login(username=self.username, password=self.password)
        ack_comment = "Acknowledging this alert now."
        initial_comment_count = AlertComment.objects.filter(alert_group=self.alert_group).count()
        initial_ack_count = AlertAcknowledgementHistory.objects.filter(alert_group=self.alert_group).count()

        response = self.client.post(self.url, {
            'acknowledge': '', # Presence triggers the logic
            'comment': ack_comment
        })

        self.assertEqual(response.status_code, 302) # Should redirect
        self.assertEqual(response.url, self.url) # Redirects back to detail view

        # Check comment was created
        self.assertEqual(AlertComment.objects.filter(alert_group=self.alert_group).count(), initial_comment_count + 1)
        new_comment = AlertComment.objects.latest('created_at')
        self.assertEqual(new_comment.content, ack_comment)
        self.assertEqual(new_comment.user, self.user)

        # Check acknowledge_alert service was called
        mock_acknowledge_alert.assert_called_once_with(self.alert_group, self.user, ack_comment)

        # Check history was created (implicitly by acknowledge_alert)
        # We can't directly check history count here as it's created within the mocked function
        # Instead, we rely on the mock assertion above.

        # Check message framework (optional, depends on if you want to test messages)
        # messages = list(get_messages(response.wsgi_request))
        # self.assertEqual(len(messages), 1)
        # self.assertEqual(str(messages[0]), "Alert has been acknowledged successfully.")

    def test_post_acknowledge_invalid_missing_comment(self):
        """Test invalid POST for acknowledgement (missing comment)."""
        self.client.login(username=self.username, password=self.password)
        initial_comment_count = AlertComment.objects.filter(alert_group=self.alert_group).count()

        response = self.client.post(self.url, {
            'acknowledge': '',
            'comment': '' # Invalid - empty comment
        })

        # Should re-render the page with form errors, not redirect
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'alerts/alert_detail.html')
        self.assertIn('acknowledge_form', response.context)
        self.assertTrue(response.context['acknowledge_form'].errors)
        self.assertIn('comment', response.context['acknowledge_form'].errors)

        # Check no comment was created
        self.assertEqual(AlertComment.objects.filter(alert_group=self.alert_group).count(), initial_comment_count)

    def test_post_comment_valid(self):
        """Test valid POST request for adding a comment."""
        self.client.login(username=self.username, password=self.password)
        comment_text = "This is a new test comment."
        initial_comment_count = AlertComment.objects.filter(alert_group=self.alert_group).count()

        response = self.client.post(self.url, {
            'content': comment_text # Use 'content' field name
        })

        self.assertEqual(response.status_code, 302) # Should redirect
        self.assertEqual(response.url, self.url)

        # Check comment was created
        self.assertEqual(AlertComment.objects.filter(alert_group=self.alert_group).count(), initial_comment_count + 1)
        new_comment = AlertComment.objects.latest('created_at')
        self.assertEqual(new_comment.content, comment_text)
        self.assertEqual(new_comment.user, self.user)

    def test_post_comment_invalid_missing_content(self):
        """Test invalid POST for comment (missing content)."""
        self.client.login(username=self.username, password=self.password)
        initial_comment_count = AlertComment.objects.filter(alert_group=self.alert_group).count()

        response = self.client.post(self.url, {
            'content': '' # Use 'content' field name - Invalid - empty comment
        })

        # Should re-render with errors now due to view change
        self.assertEqual(response.status_code, 200) # Expect 200 OK
        self.assertTemplateUsed(response, 'alerts/alert_detail.html')
        self.assertIn('comment_form', response.context)
        self.assertTrue(response.context['comment_form'].errors) # Check form has errors
        self.assertIn('content', response.context['comment_form'].errors) # Check 'content' field has error

        # Check no comment was created
        self.assertEqual(AlertComment.objects.filter(alert_group=self.alert_group).count(), initial_comment_count)

    def test_post_comment_ajax_valid(self):
        """Test valid AJAX POST for adding a comment."""
        self.client.login(username=self.username, password=self.password)
        comment_text = "This is an AJAX comment."
        initial_comment_count = AlertComment.objects.filter(alert_group=self.alert_group).count()

        response = self.client.post(self.url, {
            'content': comment_text # Use 'content' field name
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest') # AJAX header

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['user'], self.user.username)
        self.assertEqual(data['content'], comment_text)

        # Check comment was created
        self.assertEqual(AlertComment.objects.filter(alert_group=self.alert_group).count(), initial_comment_count + 1)
        new_comment = AlertComment.objects.latest('created_at')
        self.assertEqual(new_comment.content, comment_text)
        self.assertEqual(new_comment.user, self.user)

    def test_post_comment_ajax_invalid(self):
        """Test invalid AJAX POST for adding a comment."""
        self.client.login(username=self.username, password=self.password)
        initial_comment_count = AlertComment.objects.filter(alert_group=self.alert_group).count()

        response = self.client.post(self.url, {
            'content': '' # Use 'content' field name - Invalid
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest') # AJAX header

        self.assertEqual(response.status_code, 400) # Bad request
        self.assertEqual(response['content-type'], 'application/json')
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('errors', data)
        self.assertIn('content', data['errors']) # Check for content field error

        # Check no comment was created
        self.assertEqual(AlertComment.objects.filter(alert_group=self.alert_group).count(), initial_comment_count)
