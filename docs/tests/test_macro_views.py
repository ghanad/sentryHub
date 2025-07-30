from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from docs.models import Macro

User = get_user_model()

class MacroViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='tester', password='pass')
        Macro.objects.create(key='PHONE', value='1234')

    def test_macro_list_view_authenticated(self):
        self.client.login(username='tester', password='pass')
        response = self.client.get(reverse('docs:macro-list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'docs/macro_list.html')
        self.assertContains(response, 'PHONE')

    def test_macro_guide_view_requires_login(self):
        response = self.client.get(reverse('docs:macro-guide'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/accounts/login/'))

    def test_macro_guide_view_authenticated(self):
        self.client.login(username='tester', password='pass')
        response = self.client.get(reverse('docs:macro-guide'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'docs/macro_guide.html')
        self.assertContains(response, 'ماکروها')
