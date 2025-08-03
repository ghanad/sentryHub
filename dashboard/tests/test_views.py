from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User, Group
from django.utils import timezone
from datetime import timedelta
import json

from alerts.models import AlertGroup, AlertComment, AlertAcknowledgementHistory
from alerts.forms import AlertAcknowledgementForm


class DashboardViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('user', password='pass')
        self.client.login(username='user', password='pass')
        AlertGroup.objects.create(
            fingerprint='fp1',
            name='Alert1',
            labels={'instance': 'host1'},
            severity='critical',
            instance='host1',
            current_status='firing',
            acknowledged=False,
            is_silenced=False,
        )
        AlertGroup.objects.create(
            fingerprint='fp2',
            name='Alert2',
            labels={'instance': 'host2'},
            severity='warning',
            instance='host2',
            current_status='firing',
            acknowledged=True,
            is_silenced=False,
        )
        AlertGroup.objects.create(
            fingerprint='fp3',
            name='Alert3',
            labels={'instance': 'host3'},
            severity='info',
            instance='host3',
            current_status='firing',
            acknowledged=False,
            is_silenced=True,
        )

    def test_context_counts_and_charts(self):
        response = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(response.status_code, 200)
        ctx = response.context
        self.assertEqual(ctx['total_firing_alerts'], 3)
        self.assertEqual(ctx['unacknowledged_alerts'], 1)
        self.assertEqual(ctx['silenced_alerts'], 1)

        sev = json.loads(ctx['severity_distribution_json'])
        self.assertEqual(sev['data'], [1, 1, 1])

        inst = json.loads(ctx['instance_distribution_json'])
        self.assertEqual(len(inst['labels']), 3)

        daily = json.loads(ctx['daily_trend_json'])
        self.assertEqual(len(daily['labels']), 7)

        self.assertEqual(len(ctx['recent_alerts']), 3)


class Tier1AlertListViewTests(TestCase):
    def setUp(self):
        self.tier_group = Group.objects.create(name='Tier1')
        self.tier_user = User.objects.create_user('tier', password='pass')
        self.tier_user.groups.add(self.tier_group)
        self.other_user = User.objects.create_user('other', password='pass')

        AlertGroup.objects.create(
            fingerprint='fp1',
            name='Alert1',
            labels={'instance': 'host1'},
            severity='critical',
            instance='host1',
            acknowledged=False,
        )
        AlertGroup.objects.create(
            fingerprint='fp2',
            name='Alert2',
            labels={'instance': 'host2'},
            severity='critical',
            instance='host2',
            acknowledged=True,
        )

    def test_requires_tier1_or_staff(self):
        self.client.login(username='other', password='pass')
        response = self.client.get(reverse('dashboard:tier1_dashboard_new'))
        self.assertEqual(response.status_code, 403)

    def test_unacknowledged_queryset_and_context(self):
        self.client.login(username='tier', password='pass')
        response = self.client.get(reverse('dashboard:tier1_dashboard_new'))
        self.assertEqual(response.status_code, 200)
        alerts = list(response.context['alerts'])
        self.assertEqual(len(alerts), 1)
        self.assertFalse(alerts[0].acknowledged)

        ctx = response.context
        self.assertNotIn('status', ctx)
        self.assertIsInstance(ctx['acknowledge_form'], AlertAcknowledgementForm)


class AdminDashboardViewTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user('staff', password='pass', is_staff=True)
        self.user = User.objects.create_user('user', password='pass')
        self.alert = AlertGroup.objects.create(
            fingerprint='fp1',
            name='Alert1',
            labels={'instance': 'host1'},
            severity='critical',
            instance='host1',
        )
        AlertComment.objects.create(alert_group=self.alert, user=self.staff, content='hi')
        AlertAcknowledgementHistory.objects.create(alert_group=self.alert, acknowledged_by=self.staff)

    def test_requires_staff(self):
        self.client.login(username='user', password='pass')
        response = self.client.get(reverse('dashboard:admin_dashboard_summary'))
        self.assertEqual(response.status_code, 403)

    def test_context_counts(self):
        self.client.login(username='staff', password='pass')
        response = self.client.get(reverse('dashboard:admin_dashboard_summary'))
        self.assertEqual(response.status_code, 200)
        ctx = response.context
        self.assertEqual(ctx['total_comments'], 1)
        self.assertEqual(ctx['total_users'], 2)
        self.assertEqual(ctx['total_acknowledgements'], 1)
        self.assertEqual(len(ctx['recent_comments']), 1)
        self.assertEqual(len(ctx['recent_acknowledgements']), 1)


class AdminCommentsViewTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user('staff', password='pass', is_staff=True)
        self.user = User.objects.create_user('user', password='pass')
        self.alert = AlertGroup.objects.create(
            fingerprint='fp1',
            name='Alert1',
            labels={'instance': 'host1'},
            severity='critical',
            instance='host1',
        )
        self.comment = AlertComment.objects.create(alert_group=self.alert, user=self.staff, content='hi')

    def test_requires_staff(self):
        self.client.login(username='user', password='pass')
        response = self.client.get(reverse('dashboard:admin_dashboard_comments'))
        self.assertEqual(response.status_code, 403)

    def test_filters_and_context(self):
        self.client.login(username='staff', password='pass')
        today = timezone.now().date()
        response = self.client.get(reverse('dashboard:admin_dashboard_comments'), {
            'user': 'staff',
            'date_from': (today - timedelta(days=1)).isoformat(),
            'date_to': (today + timedelta(days=1)).isoformat(),
            'alert': 'Alert1',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['comments']), [self.comment])
        self.assertEqual(response.context['user_filter'], 'staff')
        self.assertEqual(response.context['alert_filter'], 'Alert1')


class AdminAcknowledgementsViewTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user('staff', password='pass', is_staff=True)
        self.user = User.objects.create_user('user', password='pass')
        self.alert = AlertGroup.objects.create(
            fingerprint='fp1',
            name='Alert1',
            labels={'instance': 'host1'},
            severity='critical',
            instance='host1',
        )
        self.ack = AlertAcknowledgementHistory.objects.create(
            alert_group=self.alert,
            acknowledged_by=self.staff,
        )

    def test_requires_staff(self):
        self.client.login(username='user', password='pass')
        response = self.client.get(reverse('dashboard:admin_dashboard_acks'))
        self.assertEqual(response.status_code, 403)

    def test_filters_and_context(self):
        self.client.login(username='staff', password='pass')
        today = timezone.now().date()
        response = self.client.get(reverse('dashboard:admin_dashboard_acks'), {
            'user': 'staff',
            'date_from': (today - timedelta(days=1)).isoformat(),
            'date_to': (today + timedelta(days=1)).isoformat(),
            'alert': 'Alert1',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['acknowledgements']), [self.ack])
        self.assertEqual(response.context['user_filter'], 'staff')
        self.assertEqual(response.context['alert_filter'], 'Alert1')
