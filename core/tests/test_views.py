from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class CoreViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')

    def test_home_view_redirects_authenticated(self):
        """
        Test that HomeView redirects authenticated users to the dashboard.
        """
        self.client.login(username='testuser', password='password')
        response = self.client.get(reverse('core:home'))
        self.assertRedirects(response, reverse('dashboard:dashboard'))

    def test_home_view_redirects_unauthenticated(self):
        """
        Test that HomeView redirects unauthenticated users to the login page.
        """
        response = self.client.get(reverse('core:home'))
        self.assertRedirects(response, reverse('login') + '?next=/')

    def test_about_view_get(self):
        """
        Test that AboutView returns a 200 status code and uses the correct template.
        """
        response = self.client.get(reverse('core:about'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/about.html')