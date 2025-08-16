from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
import json


class SmsTemplateCheckViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='tester', password='pass')
        self.client.login(username='tester', password='pass')
        self.url = reverse('integrations:sms-rule-check-template')

    def test_valid_template_returns_rendered_preview(self):
        resp = self.client.post(
            self.url,
            data=json.dumps({'template_string': 'Hello {{ alert_group.name }}'}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('Hello', data['rendered'])

    def test_invalid_template_returns_error(self):
        resp = self.client.post(
            self.url,
            data=json.dumps({'template_string': 'Hello {{ alert_group.name|invalidfilter }}'}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('Template Syntax Error', data['error'])
