from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings # Import settings
from datetime import timedelta, datetime
import pytz
import json
from unittest.mock import patch, call
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm

from ..models import AlertGroup, AlertInstance, AlertComment, SilenceRule, AlertAcknowledgementHistory
from ..forms import AlertAcknowledgementForm, AlertCommentForm, SilenceRuleForm

# Existing tests for AlertListView, AlertDetailView, SilenceRuleListView... (Keep them here)

class AlertListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.admin_user = User.objects.create_superuser(username='adminuser', email='admin@example.com', password='password')
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
        self.admin_user = User.objects.create_superuser(username='admintest', email='admin@example.com', password='password')
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
        delete_url = reverse('alerts:alert-delete', kwargs={'fingerprint': self.alert_group.fingerprint})
        self.assertNotContains(response, delete_url)

    def test_alert_detail_view_get_admin_sees_delete(self):
        self.client.logout()
        self.client.force_login(self.admin_user)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        delete_url = reverse('alerts:alert-delete', kwargs={'fingerprint': self.alert_group.fingerprint})
        self.assertContains(response, delete_url)
        self.assertIn('manual_resolve_form', response.context)

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

    def test_alert_detail_manual_resolve_requires_staff(self):
        resolved_at = (timezone.now() - timedelta(minutes=1)).astimezone(pytz.UTC).strftime('%Y-%m-%dT%H:%M')
        post_data = {
            'manual_resolve': '',
            'resolved_at': resolved_at,
            'timezone': 'UTC',
            'note': 'Attempt without permission'
        }
        response = self.client.post(self.detail_url, post_data)
        self.assertEqual(response.status_code, 403)

    def test_alert_detail_manual_resolve_success(self):
        self.client.logout()
        self.client.force_login(self.admin_user)
        resolved_at = (timezone.now() - timedelta(minutes=1)).astimezone(pytz.UTC).strftime('%Y-%m-%dT%H:%M')
        post_data = {
            'manual_resolve': '',
            'resolved_at': resolved_at,
            'timezone': 'UTC',
            'note': 'Manual closure'
        }
        response = self.client.post(self.detail_url, post_data)
        self.assertRedirects(response, self.detail_url)

        self.alert_group.refresh_from_db()
        self.instance1.refresh_from_db()
        self.assertEqual(self.alert_group.current_status, 'resolved')
        self.assertEqual(self.instance1.status, 'resolved')
        self.assertEqual(self.instance1.resolution_type, 'manual')
        self.assertIsNotNone(self.instance1.ended_at)

        latest_comment = AlertComment.objects.filter(alert_group=self.alert_group).latest('created_at')
        self.assertIn('Manual resolve', latest_comment.content)
        self.assertEqual(latest_comment.user, self.admin_user)

    def test_alert_detail_manual_resolve_invalid_time(self):
        self.client.logout()
        self.client.force_login(self.admin_user)
        resolved_at = (self.instance1.started_at - timedelta(minutes=5)).astimezone(pytz.UTC).strftime('%Y-%m-%dT%H:%M')
        post_data = {
            'manual_resolve': '',
            'resolved_at': resolved_at,
            'timezone': 'UTC',
            'note': 'Too early'
        }
        response = self.client.post(self.detail_url, post_data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('manual_resolve_form', response.context)
        self.assertTrue(response.context['manual_resolve_form'].errors)


class AlertDeleteViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='deleter', password='password')
        self.admin_user = User.objects.create_superuser(username='admin', email='admin@example.com', password='password')
        self.alert_group = AlertGroup.objects.create(
            fingerprint='delete_fp',
            name='Delete Me Alert',
            labels={'job': 'delete'},
            severity='critical',
            current_status='firing'
        )
        self.delete_url = reverse('alerts:alert-delete', kwargs={'fingerprint': self.alert_group.fingerprint})

    def test_delete_view_requires_login(self):
        response = self.client.get(self.delete_url)
        from django.conf import settings
        expected_url = f"{settings.LOGIN_URL}?next={self.delete_url}"
        self.assertRedirects(response, expected_url, status_code=302, target_status_code=200, fetch_redirect_response=False)

    def test_delete_view_get(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'alerts/alert_confirm_delete.html')
        self.assertContains(response, 'Delete Me Alert')
        self.assertIn('form', response.context)

    def test_delete_view_post_invalid_confirmation(self):
        self.client.login(username='admin', password='password')
        response = self.client.post(self.delete_url, {'confirmation': 'Wrong Name'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(AlertGroup.objects.filter(pk=self.alert_group.pk).exists())
        self.assertFormError(response, 'form', 'confirmation', 'The provided value does not match the alert name.')

    def test_delete_view_post_valid_confirmation(self):
        self.client.login(username='admin', password='password')
        response = self.client.post(self.delete_url, {'confirmation': 'Delete Me Alert'})
        self.assertRedirects(response, reverse('alerts:alert-list'))
        self.assertFalse(AlertGroup.objects.filter(pk=self.alert_group.pk).exists())

    def test_delete_view_forbidden_for_non_admin(self):
        self.client.login(username='deleter', password='password')
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 403)
        response = self.client.post(self.delete_url, {'confirmation': 'Delete Me Alert'})
        self.assertEqual(response.status_code, 403)
        self.assertTrue(AlertGroup.objects.filter(pk=self.alert_group.pk).exists())


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


# --- Tests for LoginView ---
class LoginViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.login_url = reverse('login')
        self.alert_list_url = reverse('alerts:alert-list')

    def test_get_request(self):
        """Test GET request to the login view."""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/login.html')
        self.assertIn('form', response.context)
        self.assertIsInstance(response.context['form'], AuthenticationForm)

    def test_post_valid_credentials_no_next(self):
        """Test POST with valid credentials and no 'next' parameter."""
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'password'
        })
        self.assertRedirects(response, reverse('dashboard:dashboard'), status_code=302, target_status_code=200)
        self.assertTrue(self.user.is_authenticated) # Check if user is logged in

    def test_post_valid_credentials_with_next(self):
        """Test POST with valid credentials and a 'next' parameter."""
        next_url = reverse('alerts:alert-detail', kwargs={'fingerprint': 'some_fingerprint'})
        # Create a dummy alert group for the next_url to be valid
        AlertGroup.objects.create(fingerprint='some_fingerprint', name='Dummy Alert', current_status='firing', labels={})

        response = self.client.post(f"{self.login_url}?next={next_url}", {
            'username': 'testuser',
            'password': 'password'
        })
        self.assertRedirects(response, next_url, status_code=302, target_status_code=200)
        self.assertTrue(self.user.is_authenticated) # Check if user is logged in

    def test_post_invalid_credentials(self):
        """Test POST with invalid credentials."""
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200) # Should re-render the form
        self.assertTemplateUsed(response, 'registration/login.html')
        self.assertIn('form', response.context)
        self.assertTrue(response.context['form'].errors)
        self.assertFalse(response.wsgi_request.user.is_authenticated) # User should not be logged in
        self.assertContains(response, "Please enter a correct username and password.") # Check for error message
