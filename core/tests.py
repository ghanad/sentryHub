from django.test import TestCase, Client
from django.urls import reverse

class CoreViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.home_url = reverse('core:home')
        self.about_url = reverse('core:about')

    def test_home_view(self):
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/home.html')

    def test_about_view(self):
        response = self.client.get(self.about_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/about.html') 