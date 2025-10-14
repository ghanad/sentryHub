from django.test import TestCase, Client
from django.urls import reverse
from users.models import User
from alerts.models import AlertGroup


class DashboardViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='testuser', password='password')
        cls.user.is_staff = True
        cls.user.save()

        for idx in range(25):
            AlertGroup.objects.create(
                fingerprint=f'fp-{idx}',
                name=f'Alert {idx}',
                labels={'name': f'service-{idx}'},
                severity='critical' if idx % 2 == 0 else 'warning',
                instance=f'host-{idx}',
            )

    def setUp(self):
        self.client = Client()
        self.client.login(username='testuser', password='password')

    def test_dashboard_view(self):
        response = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_tier1_dashboard_view(self):
        response = self.client.get(reverse('dashboard:tier1_dashboard_new'))
        self.assertEqual(response.status_code, 200)

    def test_tier1_dashboard_view_paginates(self):
        response = self.client.get(reverse('dashboard:tier1_dashboard_new'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_paginated'])
        self.assertEqual(response.context['paginator'].count, 25)
        self.assertEqual(len(response.context['alerts']), 20)

        response_page_two = self.client.get(reverse('dashboard:tier1_dashboard_new'), {'page': 2})
        self.assertEqual(response_page_two.status_code, 200)
        self.assertTrue(response_page_two.context['is_paginated'])
        self.assertEqual(len(response_page_two.context['alerts']), 5)

    def test_tier1_dashboard_ajax_response(self):
        response = self.client.get(
            reverse('dashboard:tier1_dashboard_new'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('rows_html', data)
        self.assertIn('modals_html', data)
        self.assertIn('pagination_html', data)
        self.assertEqual(data['alert_count'], 25)
        self.assertEqual(data['current_page'], 1)

    def test_admin_dashboard_view(self):
        response = self.client.get(reverse('dashboard:admin_dashboard_summary'))
        self.assertEqual(response.status_code, 200)

    def test_admin_comments_view(self):
        response = self.client.get(reverse('dashboard:admin_dashboard_comments'))
        self.assertEqual(response.status_code, 200)

    def test_admin_acknowledgements_view(self):
        response = self.client.get(reverse('dashboard:admin_dashboard_acks'))
        self.assertEqual(response.status_code, 200)