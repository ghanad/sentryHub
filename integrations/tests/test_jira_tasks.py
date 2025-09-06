from unittest.mock import patch
from django.test import SimpleTestCase, TestCase
from integrations.tasks import render_template_safe, JiraTaskBase, process_jira_for_alert_group
import logging
from django.test import SimpleTestCase, TestCase
from integrations.tasks import render_template_safe, JiraTaskBase, process_jira_for_alert_group
from alerts.models import AlertGroup
from integrations.models import JiraIntegrationRule

class RenderTemplateSafeTests(SimpleTestCase):
    def test_renders_valid_template(self):
        result = render_template_safe('Hello {{ name }}', {'name': 'World'})
        self.assertEqual(result, 'Hello World')

    def test_returns_default_on_error(self):
        result = render_template_safe('{% if %}', {}, 'fallback')
        self.assertEqual(result, 'fallback')

    def test_returns_default_when_empty(self):
        result = render_template_safe('', {'a': 1}, 'fallback')
        self.assertEqual(result, 'fallback')


class JiraTaskBaseTests(SimpleTestCase):
    def test_retry_configuration(self):
        self.assertEqual(JiraTaskBase.autoretry_for, (Exception,))
        self.assertEqual(JiraTaskBase.retry_kwargs['max_retries'], 3)


class RenderTemplateSafeTests(SimpleTestCase):
    def test_renders_valid_template(self):
        result = render_template_safe('Hello {{ name }}', {'name': 'World'})
        self.assertEqual(result, 'Hello World')

    def test_returns_default_on_error(self):
        result = render_template_safe('{% if %}', {}, 'fallback')
        self.assertEqual(result, 'fallback')

    def test_returns_default_when_empty(self):
        result = render_template_safe('', {'a': 1}, 'fallback')
        self.assertEqual(result, 'fallback')


class JiraTaskBaseTests(SimpleTestCase):
    def test_retry_configuration(self):
        self.assertEqual(JiraTaskBase.autoretry_for, (Exception,))
        self.assertEqual(JiraTaskBase.retry_kwargs['max_retries'], 3)


class ProcessJiraForAlertGroupTests(TestCase):
    def test_returns_when_objects_missing(self):
        # Should not raise even when provided IDs do not exist
        process_jira_for_alert_group.run(alert_group_id=999, rule_id=999, alert_status='firing', fingerprint='test-fp-123')

    def test_alertgroup_does_not_exist_logs_fingerprint(self):
        with self.assertLogs('integrations.tasks', level='ERROR') as cm:
            process_jira_for_alert_group.run(alert_group_id=999, rule_id=1, alert_status='firing', fingerprint='test-fp-456')
            self.assertIn("FP: test-fp-456", cm.output[0])
            self.assertIn("AlertGroup with ID 999 not found", cm.output[0])

    def test_jiraintegrationrule_does_not_exist_logs_fingerprint(self):
        alert_group = AlertGroup.objects.create(fingerprint='test-fp-789', name='Test Alert', source='test', labels={})
        with self.assertLogs('integrations.tasks', level='ERROR') as cm:
            process_jira_for_alert_group.run(alert_group_id=alert_group.id, rule_id=999, alert_status='firing', fingerprint='test-fp-789')
            self.assertIn("FP: test-fp-789", cm.output[0])
            self.assertIn("JiraIntegrationRule with ID 999 not found", cm.output[0])

    def test_general_exception_logs_fingerprint(self):
        # Mock AlertGroup.objects.get to raise a generic exception
        with self.assertLogs('integrations.tasks', level='ERROR') as cm:
            with patch('alerts.models.AlertGroup.objects.get', side_effect=Exception("Database error")):
                with self.assertRaises(Exception): # The task re-raises the exception
                    process_jira_for_alert_group.run(alert_group_id=1, rule_id=1, alert_status='firing', fingerprint='test-fp-abc')
            self.assertIn("FP: test-fp-abc", cm.output[0])
            self.assertIn("Error fetching base objects for AlertGroup 1: Database error", cm.output[0])
