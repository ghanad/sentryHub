from django.test import SimpleTestCase, TestCase
from integrations.tasks import render_template_safe, JiraTaskBase, process_jira_for_alert_group


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
        process_jira_for_alert_group.run(alert_group_id=999, rule_id=999, alert_status='firing')
