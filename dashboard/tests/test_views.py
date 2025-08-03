from django.test import TestCase, Client
from django.urls import reverse
from users.models import User

class DashboardViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.user.is_staff = True
        self.user.save()
        self.client.login(username='testuser', password='password')

    def test_dashboard_view(self):
        response = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_tier1_dashboard_view(self):
        response = self.client.get(reverse('dashboard:tier1_dashboard_new'))
        self.assertEqual(response.status_code, 200)

    def test_admin_dashboard_view(self):
        response = self.client.get(reverse('dashboard:admin_dashboard_summary'))
        self.assertEqual(response.status_code, 200)

    def test_admin_comments_view(self):
        response = self.client.get(reverse('dashboard:admin_dashboard_comments'))
        self.assertEqual(response.status_code, 200)

    def test_admin_acknowledgements_view(self):
        response = self.client.get(reverse('dashboard:admin_dashboard_acks'))
        self.assertEqual(response.status_code, 200)