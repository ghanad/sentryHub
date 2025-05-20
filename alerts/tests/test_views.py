from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings # Import settings
from datetime import timedelta, datetime
import json
from unittest.mock import patch, call
from django.contrib import messages # Import messages

from ..models import AlertGroup, AlertInstance, AlertComment, SilenceRule, AlertAcknowledgementHistory
from ..forms import AlertAcknowledgementForm, AlertCommentForm, SilenceRuleForm

# Existing tests for AlertListView, AlertDetailView, SilenceRuleListView... (Keep them here)

class AlertListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client.login(username='testuser', password='password')

        # Create some alert groups for testing
        self.alert1 = AlertGroup.objects.create(
            fingerprint='fp1', name='Test Alert 1', labels={'job': 'test'}, severity='critical', current_status='firing', instance='server1'
        )
        self.alert2 = AlertGroup.objects.create(
            fingerprint='fp2', name='Test Alert 2', labels={'job': 'test'}, severity='warning', current_status='resolved', instance='server2', acknowledged=True
        )
        self.alert3 = AlertGroup.objects.create(
            fingerprint='fp3', name='Another Alert', labels={'job': 'other'}, severity='info', current_status='firing', instance='server1', is_silenced=True
        )

    def test_alert_list_view_get(self):
        response = self.client.get(reverse('alerts:alert-list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'alerts/alert_list.html')
        self.assertIn('alerts', response.context)
        self.assertEqual(len(response.context['alerts']), 3) # Check if all alerts are initially listed

    def test_alert_list_view_unauthenticated(self):
        self.client.logout()
        response = self.client.get(reverse('alerts:alert-list'))
        # Use settings.LOGIN_URL which points to /users/login/
        from django.conf import settings
        expected_url = f"{settings.LOGIN_URL}?next={reverse('alerts:alert-list')}"
        self.assertRedirects(response, expected_url, status_code=302, target_status_code=200, fetch_redirect_response=False)


    def test_alert_list_filter_by_status(self):
        response = self.client.get(reverse('alerts:alert-list'), {'status': 'firing'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['alerts']), 2)
        self.assertTrue(all(a.current_status == 'firing' for a in response.context['alerts']))
        self.assertContains(response, 'Test Alert 1')
        self.assertContains(response, 'Another Alert')
        self.assertNotContains(response, 'Test Alert 2')

    def test_alert_list_filter_by_severity(self):
        response = self.client.get(reverse('alerts:alert-list'), {'severity': 'critical'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['alerts']), 1)
        self.assertEqual(response.context['alerts'][0].fingerprint, 'fp1')

    def test_alert_list_filter_by_instance(self):
        response = self.client.get(reverse('alerts:alert-list'), {'instance': 'server1'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['alerts']), 2)
        self.assertTrue(all(a.instance == 'server1' for a in response.context['alerts']))

    def test_alert_list_filter_by_acknowledged(self):
        response = self.client.get(reverse('alerts:alert-list'), {'acknowledged': 'true'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['alerts']), 1)
        self.assertEqual(response.context['alerts'][0].fingerprint, 'fp2')

        response = self.client.get(reverse('alerts:alert-list'), {'acknowledged': 'false'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['alerts']), 2)
        self.assertTrue(all(not a.acknowledged for a in response.context['alerts']))

    def test_alert_list_filter_by_silenced(self):
        response = self.client.get(reverse('alerts:alert-list'), {'silenced': 'yes'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['alerts']), 1)
        self.assertEqual(response.context['alerts'][0].fingerprint, 'fp3')

        response = self.client.get(reverse('alerts:alert-list'), {'silenced': 'no'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['alerts']), 2)
        self.assertTrue(all(not a.is_silenced for a in response.context['alerts']))

    def test_alert_list_search(self):
        response = self.client.get(reverse('alerts:alert-list'), {'search': 'Test Alert'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['alerts']), 2)
        self.assertContains(response, 'Test Alert 1')
        self.assertContains(response, 'Test Alert 2')
        self.assertNotContains(response, 'Another Alert')

        response = self.client.get(reverse('alerts:alert-list'), {'search': 'fp1'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['alerts']), 1)
        self.assertEqual(response.context['alerts'][0].fingerprint, 'fp1')

        response = self.client.get(reverse('alerts:alert-list'), {'search': 'server2'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['alerts']), 1)
        self.assertEqual(response.context['alerts'][0].fingerprint, 'fp2')

    def test_alert_list_pagination(self):
        # Create more alerts to trigger pagination (paginate_by=10)
        for i in range(4, 25):
            AlertGroup.objects.create(
                fingerprint=f'fp{i}', name=f'Test Alert {i}', labels={'job': 'test'}, severity='warning', current_status='firing'
            )
        
        response = self.client.get(reverse('alerts:alert-list'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_paginated'])
        self.assertEqual(len(response.context['alerts']), 10) # Default page size

        response = self.client.get(reverse('alerts:alert-list'), {'page': 2})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_paginated'])
        self.assertEqual(len(response.context['alerts']), 10) # Second page of alerts (3 original + 21 new = 24 total)

        # Test invalid page number (should default to page 1)
        response = self.client.get(reverse('alerts:alert-list'), {'page': 'invalid'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].number, 1)
        self.assertEqual(len(response.context['alerts']), 10)

        # Test page number too high (should default to last page)
        response = self.client.get(reverse('alerts:alert-list'), {'page': 999})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['alerts']), 4) # Last page has remaining 4 alerts (24 total / 10 per page)
        self.assertEqual(response.context['page_obj'].number, 3) # Last page is 3 (10+10+4)
        self.assertEqual(len(response.context['alerts']), 4)

        # Test page number less than 1 (should default to page 1)
        response = self.client.get(reverse('alerts:alert-list'), {'page': 0})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].number, 1)
        self.assertEqual(len(response.context['alerts']), 10) # Default page size


class AlertDetailViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client.login(username='testuser', password='password')

        self.alert_group = AlertGroup.objects.create(
            fingerprint='detail_fp', name='Detail Test Alert', labels={'job': 'detail'}, severity='warning', current_status='firing'
        )
        self.instance1 = AlertInstance.objects.create(
            alert_group=self.alert_group, status='firing', started_at=timezone.now() - timedelta(hours=1), annotations={'summary': 'Instance 1'}
        )
        self.instance2 = AlertInstance.objects.create(
            alert_group=self.alert_group, status='resolved', started_at=timezone.now() - timedelta(hours=2), ended_at=timezone.now() - timedelta(hours=1, minutes=30), annotations={'summary': 'Instance 2'}
        )
        self.comment = AlertComment.objects.create(
            alert_group=self.alert_group, user=self.user, content='Initial comment'
        )
        self.ack_history = AlertAcknowledgementHistory.objects.create(
            alert_group=self.alert_group, acknowledged_by=self.user, comment="Acknowledged"
        )
        self.detail_url = reverse('alerts:alert-detail', kwargs={'fingerprint': self.alert_group.fingerprint})

    def test_alert_detail_view_get(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'alerts/alert_detail.html')
        self.assertEqual(response.context['alert'], self.alert_group)
        self.assertIn('instances', response.context)
        self.assertIn('comments', response.context)
        self.assertIn('acknowledgement_history', response.context)
        self.assertIn('acknowledge_form', response.context)
        self.assertIn('comment_form', response.context)
        self.assertIsInstance(response.context['acknowledge_form'], AlertAcknowledgementForm)
        self.assertIsInstance(response.context['comment_form'], AlertCommentForm)
        self.assertEqual(response.context['active_tab'], 'details') # Default tab

    def test_alert_detail_view_get_specific_tab(self):
        response = self.client.get(self.detail_url, {'tab': 'history'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['active_tab'], 'history')

    def test_alert_detail_view_unauthenticated(self):
        self.client.logout()
        response = self.client.get(self.detail_url)
        # Use settings.LOGIN_URL which points to /users/login/
        from django.conf import settings
        expected_url = f"{settings.LOGIN_URL}?next={self.detail_url}"
        self.assertRedirects(response, expected_url, status_code=302, target_status_code=200, fetch_redirect_response=False)


    def test_alert_detail_view_post_acknowledge_valid(self):
        self.assertFalse(self.alert_group.acknowledged)
        post_data = {'acknowledge': '', 'comment': 'Acknowledging this alert now.'}
        response = self.client.post(self.detail_url, post_data)

        self.assertRedirects(response, self.detail_url)
        self.alert_group.refresh_from_db()
        self.assertTrue(self.alert_group.acknowledged)
        self.assertEqual(self.alert_group.acknowledged_by, self.user)
        self.assertIsNotNone(self.alert_group.acknowledgement_time)

        # Check if acknowledgement comment was created in history
        new_history = AlertAcknowledgementHistory.objects.latest('acknowledged_at')
        self.assertEqual(new_history.comment, 'Acknowledging this alert now.')
        self.assertEqual(new_history.acknowledged_by, self.user) # Corrected variable and field name

        # Check if history was created
        self.assertEqual(AlertAcknowledgementHistory.objects.filter(alert_group=self.alert_group).count(), 2)
        new_history = AlertAcknowledgementHistory.objects.latest('acknowledged_at')
        self.assertEqual(new_history.comment, 'Acknowledging this alert now.')
        self.assertEqual(new_history.acknowledged_by, self.user)

    def test_alert_detail_view_post_acknowledge_invalid_no_comment(self):
        post_data = {'acknowledge': ''} # Missing comment
        response = self.client.post(self.detail_url, post_data)

        self.assertEqual(response.status_code, 200) # Should re-render the page
        self.assertFalse(self.alert_group.acknowledged)
        self.assertIn('acknowledge_form', response.context)
        self.assertTrue(response.context['acknowledge_form'].errors)
        self.assertIn('comment', response.context['acknowledge_form'].errors)
        self.assertContains(response, "Please provide a comment") # Check for error message

    def test_alert_detail_view_post_comment_valid(self):
        post_data = {'content': 'This is a new comment.'}
        response = self.client.post(self.detail_url, post_data)

        self.assertRedirects(response, self.detail_url)
        self.assertEqual(AlertComment.objects.filter(alert_group=self.alert_group).count(), 2)
        # Retrieve the comment more specifically to avoid timestamp issues
        new_comment = AlertComment.objects.get(
            alert_group=self.alert_group,
            user=self.user,
            content='This is a new comment.'
        )
        # The get() call implicitly asserts the comment exists with the correct user and content.
        # We can keep the user assertion for extra clarity if desired.
        self.assertEqual(new_comment.user, self.user)

    def test_alert_detail_view_post_comment_invalid_empty(self):
        post_data = {'content': ''} # Empty comment
        response = self.client.post(self.detail_url, post_data)

        self.assertEqual(response.status_code, 200) # Should re-render the page
        self.assertEqual(AlertComment.objects.filter(alert_group=self.alert_group).count(), 1) # No new comment created
        self.assertIn('comment_form', response.context)
        self.assertTrue(response.context['comment_form'].errors)
        self.assertIn('content', response.context['comment_form'].errors)
        self.assertContains(response, "Please provide a valid comment") # Check for error message

    def test_alert_detail_view_post_comment_ajax_valid(self):
        post_data = {'content': 'Ajax comment'}
        response = self.client.post(self.detail_url, post_data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['user'], self.user.username)
        self.assertEqual(data['content'], 'Ajax comment')

        self.assertEqual(AlertComment.objects.filter(alert_group=self.alert_group).count(), 2)
        # Retrieve the comment more specifically to avoid timestamp issues
        new_comment = AlertComment.objects.get(
            alert_group=self.alert_group,
            user=self.user,
            content='Ajax comment'
        )
        # The get() call implicitly asserts the comment exists with the correct user and content.
        # We can keep the content assertion for extra clarity if desired.
        self.assertEqual(new_comment.content, 'Ajax comment')

    def test_alert_detail_view_post_comment_ajax_invalid(self):
        post_data = {'content': ''} # Empty comment
        response = self.client.post(self.detail_url, post_data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response['content-type'], 'application/json')
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('errors', data)
        self.assertIn('content', data['errors'])

        self.assertEqual(AlertComment.objects.filter(alert_group=self.alert_group).count(), 1) # No new comment created

    def test_alert_detail_view_post_invalid_action(self):
        # Test POSTing without 'acknowledge' or 'content'
        post_data = {'some_other_field': 'value'}
        response = self.client.post(self.detail_url, post_data)
        self.assertRedirects(response, self.detail_url) # Should just redirect back


# --- Tests for SilenceRule Views ---

class SilenceRuleListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.other_user = User.objects.create_user(username='otheruser', password='password')
        self.client.login(username='testuser', password='password')
        self.list_url = reverse('alerts:silence-rule-list')

        now = timezone.now()
        self.active_rule = SilenceRule.objects.create(
            matchers={'job': 'active'},
            starts_at=now - timedelta(hours=1),
            ends_at=now + timedelta(hours=1),
            created_by=self.user,
            comment='Active rule comment'
        )
        self.expired_rule = SilenceRule.objects.create(
            matchers={'job': 'expired'},
            starts_at=now - timedelta(days=2),
            ends_at=now - timedelta(days=1),
            created_by=self.other_user,
            comment='Expired rule comment'
        )
        self.scheduled_rule = SilenceRule.objects.create(
            matchers={'job': 'scheduled'},
            starts_at=now + timedelta(hours=1),
            ends_at=now + timedelta(hours=2),
            created_by=self.user,
            comment='Scheduled rule comment'
        )
        self.another_active_rule = SilenceRule.objects.create(
            matchers={'instance': 'server1'},
            starts_at=now - timedelta(minutes=30),
            ends_at=now + timedelta(minutes=30),
            created_by=self.other_user,
            comment='Another active rule'
        )


    def test_get_request_authenticated(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'alerts/silence_rule_list.html')
        self.assertIn('silence_rules', response.context)
        self.assertEqual(len(response.context['silence_rules']), 4) # All rules initially
        self.assertIn('status_filter', response.context)
        self.assertIn('search', response.context)
        self.assertIn('now', response.context)

    def test_get_request_unauthenticated(self):
        self.client.logout()
        response = self.client.get(self.list_url)
        # Expect a 302 redirect to the LOGIN_URL defined in settings
        from django.conf import settings
        expected_url = f"{settings.LOGIN_URL}?next={self.list_url}"
        self.assertRedirects(response, expected_url, status_code=302, target_status_code=200, fetch_redirect_response=False)

    def test_filter_by_active_status(self):
        response = self.client.get(self.list_url, {'status': 'active'})
        self.assertEqual(response.status_code, 200)
        rules = response.context['silence_rules']
        self.assertEqual(len(rules), 2)
        self.assertIn(self.active_rule, rules)
        self.assertIn(self.another_active_rule, rules)
        self.assertEqual(response.context['status_filter'], 'active')

    def test_filter_by_expired_status(self):
        response = self.client.get(self.list_url, {'status': 'expired'})
        self.assertEqual(response.status_code, 200)
        rules = response.context['silence_rules']
        self.assertEqual(len(rules), 1)
        self.assertIn(self.expired_rule, rules)
        self.assertEqual(response.context['status_filter'], 'expired')

    def test_filter_by_scheduled_status(self):
        response = self.client.get(self.list_url, {'status': 'scheduled'})
        self.assertEqual(response.status_code, 200)
        rules = response.context['silence_rules']
        self.assertEqual(len(rules), 1)
        self.assertIn(self.scheduled_rule, rules)
        self.assertEqual(response.context['status_filter'], 'scheduled')

    def test_filter_no_status(self):
        response = self.client.get(self.list_url, {'status': ''})
        self.assertEqual(response.status_code, 200)
        rules = response.context['silence_rules']
        self.assertEqual(len(rules), 4) # Shows all
        self.assertEqual(response.context['status_filter'], '')

    def test_search_by_comment(self):
        response = self.client.get(self.list_url, {'search': 'Active rule'})
        self.assertEqual(response.status_code, 200)
        rules = response.context['silence_rules']
        self.assertEqual(len(rules), 2)
        self.assertIn(self.active_rule, rules)
        self.assertIn(self.another_active_rule, rules)
        self.assertEqual(response.context['search'], 'Active rule')

    def test_search_by_creator_username(self):
        response = self.client.get(self.list_url, {'search': 'otheruser'})
        self.assertEqual(response.status_code, 200)
        rules = response.context['silence_rules']
        self.assertEqual(len(rules), 2)
        self.assertIn(self.expired_rule, rules)
        self.assertIn(self.another_active_rule, rules)
        self.assertEqual(response.context['search'], 'otheruser')

    def test_search_by_matchers_content(self):
        # Basic search within the JSON string
        response = self.client.get(self.list_url, {'search': 'server1'})
        self.assertEqual(response.status_code, 200)
        rules = response.context['silence_rules']
        self.assertEqual(len(rules), 1)
        self.assertIn(self.another_active_rule, rules)
        self.assertEqual(response.context['search'], 'server1')

        response = self.client.get(self.list_url, {'search': 'job'})
        self.assertEqual(response.status_code, 200)
        rules = response.context['silence_rules']
        # Should match active, expired, scheduled
        self.assertEqual(len(rules), 3)
        self.assertIn(self.active_rule, rules)
        self.assertIn(self.expired_rule, rules)
        self.assertIn(self.scheduled_rule, rules)

    def test_search_no_results(self):
        response = self.client.get(self.list_url, {'search': 'nonexistent'})
        self.assertEqual(response.status_code, 200)
        rules = response.context['silence_rules']
        self.assertEqual(len(rules), 0)
        self.assertEqual(response.context['search'], 'nonexistent')

    def test_default_ordering(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        rules = list(response.context['silence_rules']) # Convert queryset to list to check order
        # Expected order: scheduled, another_active, active, expired (most recent starts_at first)
        expected_order = [self.scheduled_rule, self.another_active_rule, self.active_rule, self.expired_rule]
        self.assertEqual(rules, expected_order)

    def test_pagination(self):
        # Create more rules to trigger pagination (assuming paginate_by=20)
        # 4 in setUp + 17 here = 21 total rules
        now = timezone.now()
        for i in range(5, 22): # Create 17 more rules (indices 5 through 21)
            SilenceRule.objects.create(
                matchers={'num': str(i)},
                starts_at=now - timedelta(days=i), # Vary start times for ordering
                ends_at=now + timedelta(days=1),
                created_by=self.user,
                comment=f'Rule {i}'
            )
        
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_paginated'])
        self.assertEqual(len(response.context['silence_rules']), 20) # Default page size

        # Removed print statement
        # print(f"DEBUG: Total SilenceRule objects before page 2 request: {SilenceRule.objects.count()}")
        response = self.client.get(self.list_url, {'page': 2})
        self.assertEqual(response.status_code, 200) # Check if page 2 returns 200 OK
        self.assertTrue(response.context['is_paginated'])
        self.assertEqual(len(response.context['silence_rules']), 1) # Remaining rule (4 original + 17 new = 21 total)

        # Test invalid page number (should default to page 1)
        response = self.client.get(self.list_url, {'page': 'invalid'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].number, 1)
        self.assertEqual(len(response.context['silence_rules']), 20)

        # Test page number too high (should default to last page)
        response = self.client.get(self.list_url, {'page': 999})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].number, 2) # Last page is 2
        self.assertEqual(len(response.context['silence_rules']), 1) # Last page has 1 item

        # Test page number less than 1 (should default to page 1)
        response = self.client.get(self.list_url, {'page': 0})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].number, 1)
        self.assertEqual(len(response.context['silence_rules']), 20)


class SilenceRuleCreateViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client.login(username='testuser', password='password')
        self.create_url = reverse('alerts:silence-rule-create')
        self.list_url = reverse('alerts:silence-rule-list')

        # Create some AlertGroups for testing the check_alert_silence call
        self.matching_alert = AlertGroup.objects.create(
            fingerprint='match_fp', name='Matching Alert', labels={'job': 'node', 'instance': 'server1'}, severity='warning'
        )
        self.non_matching_alert = AlertGroup.objects.create(
            fingerprint='non_match_fp', name='Non Matching Alert', labels={'job': 'other', 'instance': 'server2'}, severity='critical'
        )

    def test_get_request_authenticated(self):
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'alerts/silence_rule_form.html')
        self.assertIsInstance(response.context['form'], SilenceRuleForm)
        self.assertEqual(response.context['form_title'], "Create New Silence Rule")

    def test_get_request_unauthenticated(self):
        self.client.logout()
        response = self.client.get(self.create_url)
        # Use settings.LOGIN_URL
        expected_url = f"{settings.LOGIN_URL}?next={self.create_url}"
        self.assertRedirects(response, expected_url, status_code=302, target_status_code=200, fetch_redirect_response=False)

    def test_get_with_initial_labels_valid_json(self):
        labels = {'job': 'node', 'instance': 'server1'}
        labels_json = json.dumps(labels)
        response = self.client.get(self.create_url, {'labels': labels_json})
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        # Check initial data passed to the form instance
        self.assertEqual(form.initial.get('matchers'), labels)
        # Removed brittle check for pretty-printed JSON in response body

    @patch('alerts.views.messages') # Mock messages framework
    def test_get_with_initial_labels_invalid_json(self, mock_messages):
        labels_json = '{"job": "node", "instance": "server1"' # Invalid JSON
        response = self.client.get(self.create_url, {'labels': labels_json})
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertNotIn('matchers', form.initial) # Initial data should not be set
        # Check that messages.warning was called
        mock_messages.warning.assert_called_once_with(response.wsgi_request, "Could not pre-fill matchers: Invalid JSON.")

    @patch('alerts.views.messages') # Mock messages framework
    def test_get_with_initial_labels_not_dict(self, mock_messages):
        labels_json = '["list", "is", "not", "dict"]' # Valid JSON, but not a dict
        response = self.client.get(self.create_url, {'labels': labels_json})
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertNotIn('matchers', form.initial) # Initial data should not be set
        # Check that messages.warning was called
        mock_messages.warning.assert_called_once_with(response.wsgi_request, "Could not pre-fill matchers: Invalid label format.")

    @patch('alerts.signals.check_alert_silence') # Patch the function AS IT IS IMPORTED/USED in alerts.signals
    def test_post_valid_data(self, mock_check_alert_silence_in_signals):
        # Make test times aware using the project's default timezone
        tz = timezone.get_current_timezone()
        now = timezone.now().astimezone(tz)
        start_time = now + timedelta(minutes=5)
        end_time = now + timedelta(hours=1)
        matchers_dict = {'job': 'node', 'instance': 'server1'}
        post_data = {
            'matchers': json.dumps(matchers_dict),
            'starts_at_0': start_time.strftime('%Y-%m-%d'), # Date part
            'starts_at_1': start_time.strftime('%H:%M:%S'), # Time part
            'ends_at_0': end_time.strftime('%Y-%m-%d'),
            'ends_at_1': end_time.strftime('%H:%M:%S'),
            'comment': 'Test silence rule creation'
        }

        response = self.client.post(self.create_url, post_data)

        # Check redirect
        self.assertRedirects(response, self.list_url)

        # Check database
        self.assertEqual(SilenceRule.objects.count(), 1)
        rule = SilenceRule.objects.first()
        self.assertEqual(rule.matchers, matchers_dict)
        # Compare datetimes carefully, allowing for minor differences
        self.assertAlmostEqual(rule.starts_at, start_time, delta=timedelta(seconds=1))
        self.assertAlmostEqual(rule.ends_at, end_time, delta=timedelta(seconds=1))
        self.assertEqual(rule.comment, 'Test silence rule creation')
        self.assertEqual(rule.created_by, self.user)

        # Manually trigger the rescan logic for testing purposes
        # Assert the mock calls triggered by the post_save signal
        expected_calls = [call(self.matching_alert), call(self.non_matching_alert)]
        mock_check_alert_silence_in_signals.assert_has_calls(expected_calls, any_order=True)
        self.assertEqual(mock_check_alert_silence_in_signals.call_count, 2) # Expect 2 calls from the signal handler

        # Check for success message
        messages = list(response.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Silence rule created successfully.")

    @patch('alerts.signals.check_alert_silence') # Patch the function AS IT IS IMPORTED/USED in alerts.signals
    def test_post_valid_data_no_matching_alerts(self, mock_check_alert_silence_in_signals):
        now = timezone.now()
        start_time = now + timedelta(minutes=5)
        end_time = now + timedelta(hours=1)
        matchers_dict = {'job': 'nomatch'} # Matchers that won't match existing alerts
        post_data = {
            'matchers': json.dumps(matchers_dict),
            'starts_at_0': start_time.strftime('%Y-%m-%d'),
            'starts_at_1': start_time.strftime('%H:%M:%S'),
            'ends_at_0': end_time.strftime('%Y-%m-%d'),
            'ends_at_1': end_time.strftime('%H:%M:%S'),
            'comment': 'Test silence rule creation - no match'
        }

        response = self.client.post(self.create_url, post_data)
        self.assertRedirects(response, self.list_url)
        self.assertEqual(SilenceRule.objects.count(), 1)

        # Manually trigger the rescan logic for testing purposes
        # Assert the mock calls triggered by the post_save signal
        expected_calls = [call(self.matching_alert), call(self.non_matching_alert)]
        mock_check_alert_silence_in_signals.assert_has_calls(expected_calls, any_order=True)
        self.assertEqual(mock_check_alert_silence_in_signals.call_count, 2) # Expect 2 calls from the signal handler

        # Check for success message
        messages = list(response.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Silence rule created successfully.")


    def test_post_invalid_data_dates(self):
        now = timezone.now()
        start_time = now + timedelta(hours=1) # Start in future
        end_time = now + timedelta(minutes=30) # End before start
        matchers_dict = {'job': 'test'}
        post_data = {
            'matchers': json.dumps(matchers_dict),
            'starts_at_0': start_time.strftime('%Y-%m-%d'),
            'starts_at_1': start_time.strftime('%H:%M:%S'),
            'ends_at_0': end_time.strftime('%Y-%m-%d'),
            'ends_at_1': end_time.strftime('%H:%M:%S'),
            'comment': 'Invalid dates'
        }
        
        response = self.client.post(self.create_url, post_data)
        
        self.assertEqual(response.status_code, 200) # Re-renders form
        self.assertTemplateUsed(response, 'alerts/silence_rule_form.html')
        self.assertIn('form', response.context)
        form = response.context['form']
        self.assertTrue(form.errors)
        self.assertIn('__all__', form.errors) # Non-field error for date comparison
        self.assertIn("End time must be after start time.", form.errors['__all__'][0])
        self.assertEqual(SilenceRule.objects.count(), 0) # No rule created

    def test_post_invalid_data_matchers_json(self):
        now = timezone.now()
        start_time = now + timedelta(minutes=5)
        end_time = now + timedelta(hours=1)
        post_data = {
            'matchers': '{"job": "invalid', # Invalid JSON
            'starts_at_0': start_time.strftime('%Y-%m-%d'),
            'starts_at_1': start_time.strftime('%H:%M:%S'),
            'ends_at_0': end_time.strftime('%Y-%m-%d'),
            'ends_at_1': end_time.strftime('%H:%M:%S'),
            'comment': 'Invalid matchers'
        }
        
        response = self.client.post(self.create_url, post_data)
        
        self.assertEqual(response.status_code, 200) # Re-renders form
        self.assertTemplateUsed(response, 'alerts/silence_rule_form.html')
        self.assertIn('form', response.context)
        form = response.context['form']
        self.assertTrue(form.errors)
        self.assertIn('matchers', form.errors)
        # Expect the default JSONField error message
        self.assertIn("Enter a valid JSON.", form.errors['matchers'][0])
        self.assertEqual(SilenceRule.objects.count(), 0) # No rule created

    def test_post_missing_required_fields(self):
        post_data = {} # Empty data
        response = self.client.post(self.create_url, post_data)
        
        self.assertEqual(response.status_code, 200) # Re-renders form
        self.assertTemplateUsed(response, 'alerts/silence_rule_form.html')
        self.assertIn('form', response.context)
        form = response.context['form']
        self.assertTrue(form.errors)
        self.assertIn('matchers', form.errors)
        self.assertIn('starts_at', form.errors)
        self.assertIn('ends_at', form.errors)
        self.assertIn('comment', form.errors)
        self.assertEqual(SilenceRule.objects.count(), 0) # No rule created


# --- Placeholder for future tests ---
# class SilenceRuleUpdateViewTest(TestCase):
#     pass

# class SilenceRuleDeleteViewTest(TestCase):
#     pass

# class LoginViewTest(TestCase):
#     pass

from django.contrib.messages import get_messages
from alerts.services.alerts_processor import acknowledge_alert as acknowledge_alert_service # Alias to avoid name clash

class AcknowledgeAlertFromListViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        # self.client.login(username='testuser', password='password123') # Login will be tested per method

        self.alert_group_not_acked = AlertGroup.objects.create(
            fingerprint='fp-not-acked',
            name='Test Alert Not Acked',
            severity='critical',
            current_status='firing',
            generator_url='http://prometheus.example.com/graph?g0.expr=...',
            description='This is a test alert that is not acknowledged.',
            summary='Test Alert Summary (Not Acked)'
        )

        self.alert_group_acked = AlertGroup.objects.create(
            fingerprint='fp-acked',
            name='Test Alert Acked',
            severity='warning',
            current_status='firing',
            generator_url='http://prometheus.example.com/graph?g0.expr=...',
            acknowledged=True,
            acknowledged_by=self.user,
            acknowledgement_time=timezone.now() - timedelta(hours=1),
            summary='Test Alert Summary (Acked)'
        )
        self.acknowledge_url = reverse('alerts:acknowledge-alert-from-list')
        self.list_url = reverse('alerts:alert-list')

    @patch('alerts.views.acknowledge_alert_service') # Patch where it's used in views.py
    @patch('alerts.views.messages')
    def test_acknowledge_success(self, mock_messages, mock_acknowledge_alert_service):
        self.client.login(username='testuser', password='password123')
        fingerprint = self.alert_group_not_acked.fingerprint
        comment = "Test acknowledgement comment"
        
        # Simulate the service function's behavior (returning the updated alert group)
        mock_alert_group_updated = AlertGroup.objects.get(fingerprint=fingerprint)
        mock_alert_group_updated.acknowledged = True
        mock_alert_group_updated.acknowledged_by = self.user
        mock_alert_group_updated.acknowledgement_time = timezone.now()
        mock_acknowledge_alert_service.return_value = mock_alert_group_updated

        # Include some GET parameters in the referrer URL
        query_params = "?status=firing&severity=critical"
        referrer_url = f"{self.list_url}{query_params}"
        
        response = self.client.post(
            self.acknowledge_url,
            {'fingerprint': fingerprint, 'comment': comment},
            HTTP_REFERER=referrer_url
        )

        self.alert_group_not_acked.refresh_from_db() # Refresh from DB to see changes

        # Verify service call
        mock_acknowledge_alert_service.assert_called_once_with(
            alert_group=self.alert_group_not_acked, # Original object before service call
            user=self.user,
            comment=comment
        )
        
        # Verify AlertGroup fields (though the service is mocked, we check based on its mocked return)
        # If the service call is successful, the view uses the returned object.
        # In a real scenario, the service would update these. Here, the mock does.
        self.assertTrue(mock_alert_group_updated.acknowledged)
        self.assertEqual(mock_alert_group_updated.acknowledged_by, self.user)
        self.assertIsNotNone(mock_alert_group_updated.acknowledgement_time)

        # Check if AlertAcknowledgementHistory record was created (this is done by the service usually)
        # For this test, since the service is mocked, we can't directly test its side effects like history creation
        # *unless* the view itself creates it *after* the service call.
        # Assuming the service is responsible for history creation, we don't test it here if the service is fully mocked.
        # However, the prompt implies the view *might* be doing it or we should test it.
        # Let's assume the service `acknowledge_alert` creates the history.
        # If we want to test history creation here, the mock_acknowledge_alert_service would need to also mock history creation
        # or we'd need to not mock the service fully.
        # Given the current structure, we'll focus on what the view does *around* the service call.

        # Verify messages
        mock_messages.success.assert_called_once()
        # Call str() on the mock call's argument to compare the message content
        self.assertIn(f"Alert '{mock_alert_group_updated.name}' acknowledged.", str(mock_messages.success.call_args[0][1]))


        # Verify redirect and preserved query parameters
        self.assertRedirects(response, referrer_url, fetch_redirect_response=False)

    @patch('alerts.views.acknowledge_alert_service')
    @patch('alerts.views.messages')
    def test_acknowledge_missing_fingerprint(self, mock_messages, mock_acknowledge_alert_service):
        self.client.login(username='testuser', password='password123')
        response = self.client.post(self.acknowledge_url, {'comment': 'Some comment'})

        mock_messages.error.assert_called_once_with(response.wsgi_request, "Fingerprint is required.")
        self.assertRedirects(response, self.list_url, fetch_redirect_response=False)
        mock_acknowledge_alert_service.assert_not_called()

    @patch('alerts.views.acknowledge_alert_service')
    @patch('alerts.views.messages')
    def test_acknowledge_missing_comment(self, mock_messages, mock_acknowledge_alert_service):
        self.client.login(username='testuser', password='password123')
        fingerprint = self.alert_group_not_acked.fingerprint
        
        query_params = "?status=firing"
        referrer_url = f"{self.list_url}{query_params}"

        response = self.client.post(
            self.acknowledge_url,
            {'fingerprint': fingerprint, 'comment': ''}, # Empty comment
            HTTP_REFERER=referrer_url
        )

        mock_messages.error.assert_called_once_with(response.wsgi_request, "Comment is required to acknowledge an alert.")
        self.assertRedirects(response, referrer_url, fetch_redirect_response=False)
        mock_acknowledge_alert_service.assert_not_called()

    @patch('alerts.views.acknowledge_alert_service')
    @patch('alerts.views.messages')
    def test_acknowledge_alert_not_found(self, mock_messages, mock_acknowledge_alert_service):
        self.client.login(username='testuser', password='password123')
        response = self.client.post(
            self.acknowledge_url,
            {'fingerprint': 'non-existent-fp', 'comment': 'A comment'}
        )
        self.assertEqual(response.status_code, 404)
        mock_acknowledge_alert_service.assert_not_called()
        mock_messages.error.assert_not_called() # No message for 404

    @patch('alerts.views.acknowledge_alert_service')
    @patch('alerts.views.messages')
    def test_acknowledge_already_acknowledged(self, mock_messages, mock_acknowledge_alert_service):
        self.client.login(username='testuser', password='password123')
        fingerprint = self.alert_group_acked.fingerprint # Use the already acknowledged alert
        comment = "Trying to re-acknowledge"

        query_params = "?severity=warning"
        referrer_url = f"{self.list_url}{query_params}"

        response = self.client.post(
            self.acknowledge_url,
            {'fingerprint': fingerprint, 'comment': comment},
            HTTP_REFERER=referrer_url
        )

        mock_messages.warning.assert_called_once()
        self.assertIn(f"Alert '{self.alert_group_acked.name}' was already acknowledged.", str(mock_messages.warning.call_args[0][1]))
        self.assertRedirects(response, referrer_url, fetch_redirect_response=False)
        mock_acknowledge_alert_service.assert_not_called() # Service should not be called

    @patch('alerts.views.acknowledge_alert_service')
    @patch('alerts.views.messages')
    def test_acknowledge_service_exception(self, mock_messages, mock_acknowledge_alert_service):
        self.client.login(username='testuser', password='password123')
        fingerprint = self.alert_group_not_acked.fingerprint
        comment = "Test comment for exception"

        mock_acknowledge_alert_service.side_effect = Exception("Service unavailable")

        query_params = "?instance=serverX"
        referrer_url = f"{self.list_url}{query_params}"

        response = self.client.post(
            self.acknowledge_url,
            {'fingerprint': fingerprint, 'comment': comment},
            HTTP_REFERER=referrer_url
        )

        mock_acknowledge_alert_service.assert_called_once_with(
            alert_group=self.alert_group_not_acked,
            user=self.user,
            comment=comment
        )
        mock_messages.error.assert_called_once()
        self.assertIn(f"Could not acknowledge alert '{self.alert_group_not_acked.name}': Service unavailable", str(mock_messages.error.call_args[0][1]))
        self.assertRedirects(response, referrer_url, fetch_redirect_response=False)

    @patch('alerts.views.acknowledge_alert_service')
    @patch('alerts.views.messages')
    def test_acknowledge_unauthenticated(self, mock_messages, mock_acknowledge_alert_service):
        # No client.login() called
        fingerprint = self.alert_group_not_acked.fingerprint
        comment = "Test comment unauthenticated"
        
        response = self.client.post(
            self.acknowledge_url,
            {'fingerprint': fingerprint, 'comment': comment}
        )

        # Expect a redirect to the login page
        expected_redirect_url = f"{settings.LOGIN_URL}?next={self.acknowledge_url}"
        self.assertRedirects(response, expected_redirect_url, fetch_redirect_response=False)
        mock_acknowledge_alert_service.assert_not_called()
        mock_messages.error.assert_not_called()
        mock_messages.success.assert_not_called()

from django.contrib.auth.forms import AuthenticationForm

class LoginViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.login_url = reverse('alerts:login')
        self.alert_list_url = reverse('alerts:alert-list')

        self.active_user_username = 'activeuser'
        self.active_user_password = 'password123'
        self.active_user = User.objects.create_user(
            username=self.active_user_username,
            password=self.active_user_password,
            is_active=True
        )

        self.inactive_user_username = 'inactiveuser'
        self.inactive_user_password = 'password456'
        self.inactive_user = User.objects.create_user(
            username=self.inactive_user_username,
            password=self.inactive_user_password,
            is_active=False
        )

    def test_login_view_get_unauthenticated(self):
        """Test GET request to login page by an unauthenticated user."""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'alerts/login.html')
        self.assertIsInstance(response.context['form'], AuthenticationForm)
        self.assertFalse(response.wsgi_request.user.is_authenticated) # Ensure not accidentally logged in

    def test_login_view_get_authenticated_redirects(self):
        """Test GET request to login page by an authenticated user redirects to alert list."""
        self.client.login(username=self.active_user_username, password=self.active_user_password)
        response = self.client.get(self.login_url)
        self.assertRedirects(response, self.alert_list_url, fetch_redirect_response=False)

    def test_login_view_post_successful_login_default_redirect(self):
        """Test successful login with valid credentials redirects to alert list by default."""
        post_data = {
            'username': self.active_user_username,
            'password': self.active_user_password
        }
        response = self.client.post(self.login_url, post_data)
        self.assertRedirects(response, self.alert_list_url, fetch_redirect_response=False)
        
        # Verify user is authenticated in the session
        # One way to check is to make another request to a protected page or check session directly
        # For simplicity, we'll check if the client's session has the user_id after login
        self.assertIn('_auth_user_id', self.client.session)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.active_user.pk)

    def test_login_view_post_successful_login_with_next_redirect(self):
        """Test successful login redirects to 'next' parameter if provided."""
        next_url = reverse('alerts:silence-rule-list')
        post_data = {
            'username': self.active_user_username,
            'password': self.active_user_password
        }
        response = self.client.post(f"{self.login_url}?next={next_url}", post_data)
        self.assertRedirects(response, next_url, fetch_redirect_response=False)
        self.assertIn('_auth_user_id', self.client.session)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.active_user.pk)

    def test_user_is_authenticated_after_successful_login(self):
        """Test that request.user.is_authenticated is True after a successful login."""
        post_data = {
            'username': self.active_user_username,
            'password': self.active_user_password
        }
        self.client.post(self.login_url, post_data) # Perform login
        
        # Make a subsequent request to a simple page (e.g., alert list)
        response = self.client.get(self.alert_list_url)
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user.pk, self.active_user.pk)

    def test_login_view_post_invalid_credentials(self):
        """Test login attempt with invalid credentials."""
        post_data = {
            'username': self.active_user_username,
            'password': 'wrongpassword'
        }
        response = self.client.post(self.login_url, post_data)
        
        self.assertEqual(response.status_code, 200) # Re-renders the form
        self.assertTemplateUsed(response, 'alerts/login.html')
        self.assertIn('form', response.context)
        form = response.context['form']
        self.assertIsInstance(form, AuthenticationForm)
        self.assertTrue(form.errors) # Form should have errors
        self.assertIn('__all__', form.errors) # Django's auth form uses a non-field error for this
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        self.assertNotIn('_auth_user_id', self.client.session) # User should not be in session

    def test_login_view_post_inactive_user(self):
        """Test login attempt with credentials of an inactive user."""
        post_data = {
            'username': self.inactive_user_username,
            'password': self.inactive_user_password
        }
        response = self.client.post(self.login_url, post_data)

        self.assertEqual(response.status_code, 200) # Re-renders the form
        self.assertTemplateUsed(response, 'alerts/login.html')
        self.assertIn('form', response.context)
        form = response.context['form']
        self.assertIsInstance(form, AuthenticationForm)
        self.assertTrue(form.errors)
        self.assertIn('__all__', form.errors) 
        # Django's AuthenticationForm message for inactive user:
        self.assertIn("This account is inactive.", form.errors['__all__'][0])
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_view_post_empty_data(self):
        """Test login attempt with empty data."""
        post_data = {}
        response = self.client.post(self.login_url, post_data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'alerts/login.html')
        self.assertIn('form', response.context)
        form = response.context['form']
        self.assertTrue(form.errors)
        self.assertIn('username', form.errors)
        self.assertIn('password', form.errors)
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class SilenceRuleDeleteViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.other_user = User.objects.create_user(username='otheruser', password='password123')
        self.list_url = reverse('alerts:silence-rule-list')
        self.now = timezone.now()

        self.rule_to_delete_by_user = SilenceRule.objects.create(
            created_by=self.user,
            matchers={'severity': 'critical', 'job': 'delete_me'},
            starts_at=self.now - timedelta(hours=1),
            ends_at=self.now + timedelta(hours=1),
            comment='Rule to be deleted by user'
        )
        self.delete_url_user_rule = reverse('alerts:silence-rule-delete', kwargs={'pk': self.rule_to_delete_by_user.pk})

        self.rule_to_delete_by_other = SilenceRule.objects.create(
            created_by=self.other_user,
            matchers={'host': 'server_to_delete'},
            starts_at=self.now - timedelta(hours=1),
            ends_at=self.now + timedelta(hours=1),
            comment='Rule to be deleted by other user'
        )
        self.delete_url_other_rule = reverse('alerts:silence-rule-delete', kwargs={'pk': self.rule_to_delete_by_other.pk})
        
        # Alerts for testing re-evaluation
        self.alert_affected_by_user_rule = AlertGroup.objects.create(
            fingerprint='alert_fp_affected_user', name='Alert Affected by User Rule',
            labels={'severity': 'critical', 'job': 'delete_me'}, current_status='firing', is_silenced=True
        )
        self.alert_affected_by_other_rule = AlertGroup.objects.create(
            fingerprint='alert_fp_affected_other', name='Alert Affected by Other Rule',
            labels={'host': 'server_to_delete'}, current_status='firing', is_silenced=True
        )
        self.alert_not_affected = AlertGroup.objects.create(
            fingerprint='alert_fp_not_affected_delete', name='Alert Not Affected by Deletion',
            labels={'service': 'other_service'}, current_status='firing'
        )

    def test_delete_view_unauthenticated_get(self):
        """Test GET request to delete view by unauthenticated user."""
        response = self.client.get(self.delete_url_user_rule)
        expected_url = f"{settings.LOGIN_URL}?next={self.delete_url_user_rule}"
        self.assertRedirects(response, expected_url, status_code=302, target_status_code=200, fetch_redirect_response=False)

    def test_delete_view_unauthenticated_post(self):
        """Test POST request to delete view by unauthenticated user."""
        response = self.client.post(self.delete_url_user_rule)
        expected_url = f"{settings.LOGIN_URL}?next={self.delete_url_user_rule}"
        self.assertRedirects(response, expected_url, status_code=302, target_status_code=200, fetch_redirect_response=False)
        self.assertTrue(SilenceRule.objects.filter(pk=self.rule_to_delete_by_user.pk).exists()) # Rule should still exist

    def test_delete_view_authenticated_get_own_rule(self):
        """Test GET request by authenticated user for their own rule's delete confirmation page."""
        self.client.login(username='testuser', password='password123')
        response = self.client.get(self.delete_url_user_rule)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'alerts/silence_rule_confirm_delete.html')
        self.assertIn('object', response.context)
        self.assertEqual(response.context['object'], self.rule_to_delete_by_user)
        self.assertContains(response, f"Are you sure you want to delete the silence rule: {self.rule_to_delete_by_user.id}?")

    def test_delete_view_authenticated_get_other_user_rule(self):
        """Test GET request by authenticated user for another user's rule's delete page (should be allowed)."""
        self.client.login(username='testuser', password='password123')
        response = self.client.get(self.delete_url_other_rule)
        self.assertEqual(response.status_code, 200) # Assuming users can delete others' rules
        self.assertTemplateUsed(response, 'alerts/silence_rule_confirm_delete.html')
        self.assertEqual(response.context['object'], self.rule_to_delete_by_other)

    def test_delete_view_get_non_existent_rule(self):
        """Test GET request for deleting a non-existent rule."""
        self.client.login(username='testuser', password='password123')
        non_existent_url = reverse('alerts:silence-rule-delete', kwargs={'pk': 9999})
        response = self.client.get(non_existent_url)
        self.assertEqual(response.status_code, 404)

    @patch('alerts.views.messages')
    @patch('alerts.signals.check_alert_silence_for_all_alerts') # Patch the signal handler's target
    def test_delete_view_post_successful_delete_own_rule(self, mock_check_all_alerts, mock_messages):
        self.client.login(username='testuser', password='password123')
        rule_pk = self.rule_to_delete_by_user.pk
        rule_id_for_message = self.rule_to_delete_by_user.id # Get id before deletion for message check

        response = self.client.post(self.delete_url_user_rule)

        self.assertRedirects(response, self.list_url, fetch_redirect_response=False)
        self.assertFalse(SilenceRule.objects.filter(pk=rule_pk).exists())
        mock_messages.success.assert_called_once_with(response.wsgi_request, f"Silence rule '{rule_id_for_message}' deleted successfully.")
        
        # Check that the signal handler was called to re-evaluate alerts
        # The signal handler is called after the object is deleted.
        mock_check_all_alerts.assert_called_once()
        # We could check the arguments passed to mock_check_all_alerts if needed, e.g.,
        # to ensure it's called with the matchers of the deleted rule or similar context.
        # For now, just ensuring it's called is the primary goal.

    @patch('alerts.views.messages')
    @patch('alerts.signals.check_alert_silence_for_all_alerts')
    def test_delete_view_post_successful_delete_other_user_rule(self, mock_check_all_alerts, mock_messages):
        """ Test deleting another user's rule (assuming no specific permission restrictions beyond login) """
        self.client.login(username='testuser', password='password123') # Logged in as 'testuser'
        rule_pk = self.rule_to_delete_by_other.pk
        rule_id_for_message = self.rule_to_delete_by_other.id

        response = self.client.post(self.delete_url_other_rule)

        self.assertRedirects(response, self.list_url, fetch_redirect_response=False)
        self.assertFalse(SilenceRule.objects.filter(pk=rule_pk).exists())
        mock_messages.success.assert_called_once_with(response.wsgi_request, f"Silence rule '{rule_id_for_message}' deleted successfully.")
        mock_check_all_alerts.assert_called_once()

    @patch('alerts.views.messages')
    @patch('alerts.signals.check_alert_silence_for_all_alerts')
    def test_delete_view_post_non_existent_rule(self, mock_check_all_alerts, mock_messages):
        """Test POST request for deleting a non-existent rule."""
        self.client.login(username='testuser', password='password123')
        non_existent_url = reverse('alerts:silence-rule-delete', kwargs={'pk': 9999})
        response = self.client.post(non_existent_url)
        self.assertEqual(response.status_code, 404)
        mock_messages.success.assert_not_called()
        mock_check_all_alerts.assert_not_called()


class SilenceRuleUpdateViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123', email='test@example.com')
        self.other_user = User.objects.create_user(username='otheruser', password='password123')
        self.list_url = reverse('alerts:silence-rule-list')

        # Timezone-aware datetime for consistent testing
        self.now = timezone.now()
        self.starts_at_initial = self.now + timedelta(hours=1)
        self.ends_at_initial = self.now + timedelta(hours=2)

        self.rule_by_user = SilenceRule.objects.create(
            created_by=self.user,
            matchers={'severity': 'critical', 'job': 'rule1'},
            starts_at=self.starts_at_initial,
            ends_at=self.ends_at_initial,
            comment='Initial comment by user'
        )
        self.update_url_user_rule = reverse('alerts:silence-rule-update', kwargs={'pk': self.rule_by_user.pk})

        self.rule_by_other = SilenceRule.objects.create(
            created_by=self.other_user,
            matchers={'host': 'serverA'},
            starts_at=self.now + timedelta(days=1),
            ends_at=self.now + timedelta(days=2),
            comment='Initial comment by other user'
        )
        self.update_url_other_rule = reverse('alerts:silence-rule-update', kwargs={'pk': self.rule_by_other.pk})

        # Alerts for testing re-evaluation
        self.alert_matching_initial = AlertGroup.objects.create(
            fingerprint='alert_fp_match_initial', name='Alert Match Initial',
            labels={'severity': 'critical', 'job': 'rule1'}, current_status='firing'
        )
        self.alert_matching_updated = AlertGroup.objects.create(
            fingerprint='alert_fp_match_updated', name='Alert Match Updated',
            labels={'severity': 'warning', 'job': 'rule_updated'}, current_status='firing'
        )
        self.alert_not_matching = AlertGroup.objects.create(
            fingerprint='alert_fp_no_match', name='Alert No Match',
            labels={'service': 'web'}, current_status='firing'
        )

    def test_update_view_unauthenticated_get(self):
        """Test GET request to update view by unauthenticated user."""
        response = self.client.get(self.update_url_user_rule)
        expected_url = f"{settings.LOGIN_URL}?next={self.update_url_user_rule}"
        self.assertRedirects(response, expected_url, status_code=302, target_status_code=200, fetch_redirect_response=False)

    def test_update_view_unauthenticated_post(self):
        """Test POST request to update view by unauthenticated user."""
        post_data = {
            'matchers': json.dumps({'severity': 'warning'}),
            'starts_at_0': (self.now + timedelta(hours=3)).strftime('%Y-%m-%d'),
            'starts_at_1': (self.now + timedelta(hours=3)).strftime('%H:%M:%S'),
            'ends_at_0': (self.now + timedelta(hours=4)).strftime('%Y-%m-%d'),
            'ends_at_1': (self.now + timedelta(hours=4)).strftime('%H:%M:%S'),
            'comment': 'Attempted update by unauthenticated user'
        }
        response = self.client.post(self.update_url_user_rule, post_data)
        expected_url = f"{settings.LOGIN_URL}?next={self.update_url_user_rule}"
        self.assertRedirects(response, expected_url, status_code=302, target_status_code=200, fetch_redirect_response=False)
        
        # Verify the rule was not changed
        self.rule_by_user.refresh_from_db()
        self.assertEqual(self.rule_by_user.matchers, {'severity': 'critical', 'job': 'rule1'})
        self.assertEqual(self.rule_by_user.comment, 'Initial comment by user')

    def test_update_view_authenticated_get_own_rule(self):
        """Test GET request by authenticated user for their own rule."""
        self.client.login(username='testuser', password='password123')
        response = self.client.get(self.update_url_user_rule)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'alerts/silence_rule_form.html')
        self.assertIsInstance(response.context['form'], SilenceRuleForm)
        self.assertEqual(response.context['form_title'], f"Update Silence Rule: {self.rule_by_user.id}")
        self.assertIn('now', response.context) # Check for 'now' in context

        form = response.context['form']
        self.assertEqual(form.initial['comment'], self.rule_by_user.comment)
        # Matchers are rendered as JSON string in the widget
        self.assertEqual(json.loads(form.fields['matchers'].widget.attrs['value']), self.rule_by_user.matchers)
        self.assertEqual(form.initial['starts_at'], self.rule_by_user.starts_at)
        self.assertEqual(form.initial['ends_at'], self.rule_by_user.ends_at)

    def test_update_view_authenticated_get_other_user_rule(self):
        """Test GET request by authenticated user for another user's rule (should be allowed)."""
        self.client.login(username='testuser', password='password123')
        response = self.client.get(self.update_url_other_rule)
        self.assertEqual(response.status_code, 200) # Assuming no specific permission check for viewing/editing others' rules
        self.assertTemplateUsed(response, 'alerts/silence_rule_form.html')
        form = response.context['form']
        self.assertEqual(form.initial['comment'], self.rule_by_other.comment)
        self.assertEqual(json.loads(form.fields['matchers'].widget.attrs['value']), self.rule_by_other.matchers)

    def test_update_view_get_non_existent_rule(self):
        """Test GET request for a non-existent rule."""
        self.client.login(username='testuser', password='password123')
        non_existent_url = reverse('alerts:silence-rule-update', kwargs={'pk': 9999})
        response = self.client.get(non_existent_url)
        self.assertEqual(response.status_code, 404)

    @patch('alerts.views.messages')
    @patch('alerts.signals.check_alert_silence') # Patch where it's imported in signals
    def test_update_view_post_successful_update_own_rule(self, mock_check_alert_silence, mock_messages):
        self.client.login(username='testuser', password='password123')
        
        updated_matchers = {'severity': 'warning', 'job': 'rule_updated'}
        updated_comment = 'Updated comment for rule by user.'
        updated_starts_at = self.now + timedelta(hours=5)
        updated_ends_at = self.now + timedelta(hours=10)

        post_data = {
            'matchers': json.dumps(updated_matchers),
            'starts_at_0': updated_starts_at.strftime('%Y-%m-%d'),
            'starts_at_1': updated_starts_at.strftime('%H:%M:%S'),
            'ends_at_0': updated_ends_at.strftime('%Y-%m-%d'),
            'ends_at_1': updated_ends_at.strftime('%H:%M:%S'),
            'comment': updated_comment
        }
        response = self.client.post(self.update_url_user_rule, post_data)

        self.assertRedirects(response, self.list_url, fetch_redirect_response=False)
        
        self.rule_by_user.refresh_from_db()
        self.assertEqual(self.rule_by_user.matchers, updated_matchers)
        self.assertEqual(self.rule_by_user.comment, updated_comment)
        self.assertAlmostEqual(self.rule_by_user.starts_at, updated_starts_at, delta=timedelta(seconds=1))
        self.assertAlmostEqual(self.rule_by_user.ends_at, updated_ends_at, delta=timedelta(seconds=1))
        self.assertEqual(self.rule_by_user.created_by, self.user) # Should not change

        mock_messages.success.assert_called_once_with(response.wsgi_request, f"Silence rule '{self.rule_by_user.id}' updated successfully.")
        
        # Verify check_alert_silence calls
        # It should be called for all alerts that might be affected.
        # In the test setup, these are alert_matching_initial (was matching, might not now)
        # and alert_matching_updated (was not matching, might be now)
        # and alert_not_matching (was not matching, still should not)
        expected_calls = [
            call(self.alert_matching_initial), 
            call(self.alert_matching_updated),
            call(self.alert_not_matching)
        ]
        mock_check_alert_silence.assert_has_calls(expected_calls, any_order=True)
        self.assertEqual(mock_check_alert_silence.call_count, AlertGroup.objects.count())


    @patch('alerts.views.messages')
    @patch('alerts.signals.check_alert_silence')
    def test_update_view_post_successful_update_other_user_rule(self, mock_check_alert_silence, mock_messages):
        """ Test updating another user's rule (assuming no specific permission restrictions beyond login) """
        self.client.login(username='testuser', password='password123') # Logged in as 'testuser'

        updated_matchers = {'host': 'serverB', 'service': 'db'}
        updated_comment = 'Updated comment for other user rule by testuser.'
        updated_starts_at = self.now + timedelta(days=3)
        updated_ends_at = self.now + timedelta(days=4)

        post_data = {
            'matchers': json.dumps(updated_matchers),
            'starts_at_0': updated_starts_at.strftime('%Y-%m-%d'),
            'starts_at_1': updated_starts_at.strftime('%H:%M:%S'),
            'ends_at_0': updated_ends_at.strftime('%Y-%m-%d'),
            'ends_at_1': updated_ends_at.strftime('%H:%M:%S'),
            'comment': updated_comment
        }
        response = self.client.post(self.update_url_other_rule, post_data)

        self.assertRedirects(response, self.list_url, fetch_redirect_response=False)
        
        self.rule_by_other.refresh_from_db()
        self.assertEqual(self.rule_by_other.matchers, updated_matchers)
        self.assertEqual(self.rule_by_other.comment, updated_comment)
        self.assertAlmostEqual(self.rule_by_other.starts_at, updated_starts_at, delta=timedelta(seconds=1))
        self.assertAlmostEqual(self.rule_by_other.ends_at, updated_ends_at, delta=timedelta(seconds=1))
        self.assertEqual(self.rule_by_other.created_by, self.other_user) # Original creator should persist

        mock_messages.success.assert_called_once_with(response.wsgi_request, f"Silence rule '{self.rule_by_other.id}' updated successfully.")
        self.assertEqual(mock_check_alert_silence.call_count, AlertGroup.objects.count())

    @patch('alerts.views.messages')
    @patch('alerts.signals.check_alert_silence')
    def test_update_view_post_empty_matchers(self, mock_check_alert_silence, mock_messages):
        """Test updating a rule to have empty matchers. """
        self.client.login(username='testuser', password='password123')
        
        updated_comment = 'Updated with empty matchers.'
        post_data = {
            'matchers': json.dumps({}), # Empty matchers
            'starts_at_0': self.starts_at_initial.strftime('%Y-%m-%d'),
            'starts_at_1': self.starts_at_initial.strftime('%H:%M:%S'),
            'ends_at_0': self.ends_at_initial.strftime('%Y-%m-%d'),
            'ends_at_1': self.ends_at_initial.strftime('%H:%M:%S'),
            'comment': updated_comment
        }
        response = self.client.post(self.update_url_user_rule, post_data)

        self.assertRedirects(response, self.list_url, fetch_redirect_response=False)
        self.rule_by_user.refresh_from_db()
        self.assertEqual(self.rule_by_user.matchers, {})
        self.assertEqual(self.rule_by_user.comment, updated_comment)
        
        mock_messages.success.assert_called_once()
        # The signal handler for check_alert_silence will still be called for all alerts
        # to re-evaluate if they are now unsilenced or remain silenced (if they were by other rules).
        self.assertEqual(mock_check_alert_silence.call_count, AlertGroup.objects.count())

    @patch('alerts.views.messages')
    @patch('alerts.signals.check_alert_silence') # Patch where it's imported in signals
    def test_update_view_post_invalid_dates(self, mock_check_alert_silence, mock_messages):
        self.client.login(username='testuser', password='password123')
        
        original_comment = self.rule_by_user.comment
        original_matchers = self.rule_by_user.matchers

        # ends_at before starts_at
        invalid_starts_at = self.now + timedelta(hours=2)
        invalid_ends_at = self.now + timedelta(hours=1)

        post_data = {
            'matchers': json.dumps(self.rule_by_user.matchers),
            'starts_at_0': invalid_starts_at.strftime('%Y-%m-%d'),
            'starts_at_1': invalid_starts_at.strftime('%H:%M:%S'),
            'ends_at_0': invalid_ends_at.strftime('%Y-%m-%d'),
            'ends_at_1': invalid_ends_at.strftime('%H:%M:%S'),
            'comment': 'Attempting invalid date update'
        }
        response = self.client.post(self.update_url_user_rule, post_data)

        self.assertEqual(response.status_code, 200) # Re-renders form
        self.assertTemplateUsed(response, 'alerts/silence_rule_form.html')
        form = response.context['form']
        self.assertTrue(form.errors)
        self.assertIn('__all__', form.errors) # Non-field error for date comparison
        self.assertIn("End time must be after start time.", form.errors['__all__'][0])
        
        self.rule_by_user.refresh_from_db()
        self.assertEqual(self.rule_by_user.comment, original_comment) # Data should not have changed
        self.assertEqual(self.rule_by_user.matchers, original_matchers)

        mock_messages.error.assert_not_called() # Form errors are displayed, not via messages framework for this type of error
        mock_check_alert_silence.assert_not_called() # Form validation fails before signal

    @patch('alerts.views.messages')
    @patch('alerts.signals.check_alert_silence')
    def test_update_view_post_invalid_matchers_json(self, mock_check_alert_silence, mock_messages):
        self.client.login(username='testuser', password='password123')
        original_comment = self.rule_by_user.comment

        post_data = {
            'matchers': '{"job": "invalid_json', # Invalid JSON string
            'starts_at_0': self.starts_at_initial.strftime('%Y-%m-%d'),
            'starts_at_1': self.starts_at_initial.strftime('%H:%M:%S'),
            'ends_at_0': self.ends_at_initial.strftime('%Y-%m-%d'),
            'ends_at_1': self.ends_at_initial.strftime('%H:%M:%S'),
            'comment': 'Attempting invalid JSON update'
        }
        response = self.client.post(self.update_url_user_rule, post_data)

        self.assertEqual(response.status_code, 200) # Re-renders form
        self.assertTemplateUsed(response, 'alerts/silence_rule_form.html')
        form = response.context['form']
        self.assertTrue(form.errors)
        self.assertIn('matchers', form.errors)
        self.assertIn("Enter a valid JSON.", form.errors['matchers'][0])
        
        self.rule_by_user.refresh_from_db()
        self.assertEqual(self.rule_by_user.comment, original_comment) # Data should not have changed

        mock_check_alert_silence.assert_not_called()

    @patch('alerts.views.messages')
    @patch('alerts.signals.check_alert_silence')
    def test_update_view_post_missing_required_field_comment(self, mock_check_alert_silence, mock_messages):
        self.client.login(username='testuser', password='password123')
        original_matchers = self.rule_by_user.matchers

        post_data = {
            'matchers': json.dumps(self.rule_by_user.matchers),
            'starts_at_0': self.starts_at_initial.strftime('%Y-%m-%d'),
            'starts_at_1': self.starts_at_initial.strftime('%H:%M:%S'),
            'ends_at_0': self.ends_at_initial.strftime('%Y-%m-%d'),
            'ends_at_1': self.ends_at_initial.strftime('%H:%M:%S'),
            'comment': '' # Missing comment
        }
        response = self.client.post(self.update_url_user_rule, post_data)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'alerts/silence_rule_form.html')
        form = response.context['form']
        self.assertTrue(form.errors)
        self.assertIn('comment', form.errors)
        self.assertIn("This field is required.", form.errors['comment'][0])

        self.rule_by_user.refresh_from_db()
        self.assertEqual(self.rule_by_user.matchers, original_matchers)
        mock_check_alert_silence.assert_not_called()

    @patch('alerts.views.messages')
    @patch('alerts.views.check_alert_silence_for_all_alerts') # Patch this function in views.py
    def test_update_view_post_check_alert_silence_calls(self, mock_check_all_alerts, mock_messages):
        self.client.login(username='testuser', password='password123')
        
        initial_matchers_str = json.dumps(self.rule_by_user.matchers)
        updated_matchers = {'severity': 'high', 'service': 'new_service'}
        updated_comment = 'Testing check_alert_silence calls.'
        
        post_data = {
            'matchers': json.dumps(updated_matchers), # Matchers changed
            'starts_at_0': self.starts_at_initial.strftime('%Y-%m-%d'), # Dates unchanged
            'starts_at_1': self.starts_at_initial.strftime('%H:%M:%S'),
            'ends_at_0': self.ends_at_initial.strftime('%Y-%m-%d'),
            'ends_at_1': self.ends_at_initial.strftime('%H:%M:%S'),
            'comment': updated_comment # Comment changed
        }
        
        # Store initial field values to compare
        old_comment = self.rule_by_user.comment
        old_starts_at = self.rule_by_user.starts_at
        
        response = self.client.post(self.update_url_user_rule, post_data)
        self.assertRedirects(response, self.list_url)

        self.rule_by_user.refresh_from_db()

        # Check that the signal handler was called.
        # The view's form_valid sends a signal, which then calls check_alert_silence_for_all_alerts.
        # We are testing that the signal was sent and the handler called.
        mock_check_all_alerts.assert_called_once()
        
        # We can also inspect the arguments if needed, but the core is that it's called.
        # Example: mock_check_all_alerts.assert_called_once_with(old_matchers_list=[self.rule_by_user.matchers_as_list_of_dicts()], new_matchers_list=[updated_matchers_as_list])
        # This would require more complex setup of matchers_as_list_of_dicts on the model or in the test.

        # Verify that the updated_fields were correctly identified by the form's save method
        # (This is an internal check of the form's behavior, which influences the signal)
        form = SilenceRuleForm(data=post_data, instance=self.rule_by_user)
        self.assertTrue(form.is_valid()) 
        
        # The actual updated_fields list is part of the form's internal save process, 
        # which then is used by the signal. We're ensuring the conditions for the signal are met.
        # The important part is that check_alert_silence_for_all_alerts was called because fields changed.
        
        # Case 2: Only comment changes, matchers and times do not.
        # check_alert_silence_for_all_alerts should NOT be called if only comment changes.
        mock_check_all_alerts.reset_mock()
        only_comment_changed_post_data = {
            'matchers': json.dumps(updated_matchers), # Keep matchers same as last update
            'starts_at_0': self.starts_at_initial.strftime('%Y-%m-%d'), 
            'starts_at_1': self.starts_at_initial.strftime('%H:%M:%S'),
            'ends_at_0': self.ends_at_initial.strftime('%Y-%m-%d'),
            'ends_at_1': self.ends_at_initial.strftime('%H:%M:%S'),
            'comment': "Only comment changed now."
        }
        response = self.client.post(self.update_url_user_rule, only_comment_changed_post_data)
        self.assertRedirects(response, self.list_url)
        # Since only comment changed, the signal should not have triggered check_alert_silence_for_all_alerts
        # *if* the signal handler checks for relevant field changes.
        # The current signal handler `silence_rule_updated_or_deleted` in `alerts/signals.py`
        # calls `check_alert_silence_for_all_alerts` unconditionally on post_save.
        # Therefore, it *will* be called.
        mock_check_all_alerts.assert_called_once()


    @patch('alerts.views.messages')
    @patch('alerts.signals.check_alert_silence_for_all_alerts') # Patch the signal handler's target
    def test_update_view_post_no_relevant_field_change(self, mock_check_all_alerts_in_signals, mock_messages):
        """ Test that check_alert_silence_for_all_alerts is NOT called if only non-critical fields (like comment) change.
            This test assumes the signal handler is smart enough to check `update_fields`.
            However, the current `silence_rule_updated_or_deleted` signal handler calls
            `check_alert_silence_for_all_alerts` unconditionally on `post_save`.
            Thus, this test will reflect the current behavior (it WILL be called).
            If the signal handler were to be optimized, this test would change its assertion for mock_check_all_alerts_in_signals.
        """
        self.client.login(username='testuser', password='password123')
        
        # Data where only the comment changes
        post_data_comment_only = {
            'matchers': json.dumps(self.rule_by_user.matchers), # Matchers same
            'starts_at_0': self.rule_by_user.starts_at.strftime('%Y-%m-%d'), # Dates same
            'starts_at_1': self.rule_by_user.starts_at.strftime('%H:%M:%S'),
            'ends_at_0': self.rule_by_user.ends_at.strftime('%Y-%m-%d'),
            'ends_at_1': self.rule_by_user.ends_at.strftime('%H:%M:%S'),
            'comment': 'Only the comment is updated here.' # Comment changed
        }
        
        response = self.client.post(self.update_url_user_rule, post_data_comment_only)
        self.assertRedirects(response, self.list_url)
        self.rule_by_user.refresh_from_db()
        self.assertEqual(self.rule_by_user.comment, 'Only the comment is updated here.')
        
        # Current behavior: signal handler calls check_alert_silence_for_all_alerts even if only comment changed.
        mock_check_all_alerts_in_signals.assert_called_once()
        # If signal handler was optimized:
        # mock_check_all_alerts_in_signals.assert_not_called() 
        # And the success message would indicate only comment changed.
        mock_messages.success.assert_called_once_with(response.wsgi_request, f"Silence rule '{self.rule_by_user.id}' updated successfully.")

    @patch('alerts.views.acknowledge_alert_service')
    @patch('alerts.views.messages')
    def test_acknowledge_get_request_not_allowed(self, mock_messages, mock_acknowledge_alert_service):
        self.client.login(username='testuser', password='password123')
        # Make a GET request instead of POST
        response = self.client.get(self.acknowledge_url) 
        
        self.assertEqual(response.status_code, 405) # Method Not Allowed
        mock_acknowledge_alert_service.assert_not_called()
        mock_messages.error.assert_not_called()
        mock_messages.success.assert_not_called()
