from django.test import TestCase
from unittest.mock import patch

from alerts.models import AlertGroup
from django.utils import timezone
from integrations.models import SlackIntegrationRule
from integrations.services.slack_matcher import SlackRuleMatcherService
from integrations.services.slack_service import SlackNotificationError
from integrations.tasks import process_slack_for_alert_group, sanitize_ip_addresses
from celery.exceptions import Retry


class SlackMatcherTests(TestCase):
    def setUp(self):
        self.alert_group = AlertGroup.objects.create(
            fingerprint='fp1',
            name='Test',
            labels={'app': 'api', 'env': 'prod'},
            source='prometheus',
        )

    def test_matches_most_specific_rule(self):
        rule_generic = SlackIntegrationRule.objects.create(
            name='generic',
            slack_channel='#general',
            match_criteria={'labels__app': 'api'},
        )
        rule_specific = SlackIntegrationRule.objects.create(
            name='specific',
            slack_channel='#alerts',
            match_criteria={'labels__app': 'api', 'source': 'prometheus'},
        )
        matcher = SlackRuleMatcherService()
        matched = matcher.find_matching_rule(self.alert_group)
        self.assertEqual(matched, rule_specific)

    def test_returns_none_when_no_rule_matches(self):
        SlackIntegrationRule.objects.create(
            name='nope',
            slack_channel='#general',
            match_criteria={'labels__app': 'web'},
        )
        matcher = SlackRuleMatcherService()
        matched = matcher.find_matching_rule(self.alert_group)
        self.assertIsNone(matched)


class SlackTaskTests(TestCase):
    @patch('integrations.tasks.SlackService')
    def test_process_slack_for_alert_group_renders_alert_group(self, mock_service_cls):
        mock_service = mock_service_cls.return_value
        mock_service.send_notification.return_value = True

        alert_group = AlertGroup.objects.create(
            fingerprint='fp2',
            name='AG2',
            labels={'app': 'foo'},
            source='prometheus',
        )
        rule = SlackIntegrationRule.objects.create(
            name='rule',
            slack_channel='#chan',
            match_criteria={},
            message_template='{{ alert_group.labels.app }}',
        )

        process_slack_for_alert_group(alert_group.id, rule.id)

        mock_service.send_notification.assert_called_once_with('#chan', 'foo')

    @patch('integrations.tasks.SlackService')
    def test_logs_include_fingerprint(self, mock_service_cls):
        mock_service = mock_service_cls.return_value
        mock_service.send_notification.return_value = True

        alert_group = AlertGroup.objects.create(
            fingerprint='fp3',
            name='AG3',
            labels={'app': 'bar'},
            source='prometheus',
        )
        rule = SlackIntegrationRule.objects.create(
            name='rule',
            slack_channel='#chan',
            match_criteria={},
            message_template='{{ alert_group.labels.app }}',
        )

        with self.assertLogs('integrations.tasks', level='INFO') as cm:
            process_slack_for_alert_group(alert_group.id, rule.id)

        log_output = ' '.join(cm.output)
        self.assertIn(f"(FP: {alert_group.fingerprint})", log_output)

    @patch('integrations.tasks.SlackService')
    def test_process_slack_for_alert_group_uses_annotations(self, mock_service_cls):
        mock_service = mock_service_cls.return_value
        mock_service.send_notification.return_value = True

        alert_group = AlertGroup.objects.create(
            fingerprint='fp4',
            name='AG4',
            labels={'app': 'baz'},
            source='prometheus',
        )
        # create AlertInstance with annotations
        alert_group.instances.create(
            status='firing',
            started_at=timezone.now(),
            annotations={'summary': 'Summary text', 'description': 'More details'},
        )

        rule = SlackIntegrationRule.objects.create(
            name='rule',
            slack_channel='#chan',
            match_criteria={},
            message_template='{{ summary }} -- {{ description }}',
        )

        process_slack_for_alert_group(alert_group.id, rule.id)

        mock_service.send_notification.assert_called_once_with('#chan', 'Summary text -- More details')

    @patch('integrations.tasks.SlackService')
    def test_process_slack_for_alert_group_sanitizes_ipv4_with_port(self, mock_service_cls):
        mock_service = mock_service_cls.return_value
        mock_service.send_notification.return_value = True

        alert_group = AlertGroup.objects.create(
            fingerprint='fp5',
            name='AG5',
            labels={'app': 'app'},
            source='prometheus',
        )
        rule = SlackIntegrationRule.objects.create(
            name='rule',
            slack_channel='#chan',
            match_criteria={},
            message_template='Alert on 192.168.1.10:9100 is firing.',
        )

        process_slack_for_alert_group(alert_group.id, rule.id)

        mock_service.send_notification.assert_called_once_with('#chan', 'Alert on IP is firing.')

    @patch('integrations.tasks.SlackService')
    def test_process_slack_for_alert_group_sanitizes_ipv6(self, mock_service_cls):
        mock_service = mock_service_cls.return_value
        mock_service.send_notification.return_value = True

        alert_group = AlertGroup.objects.create(
            fingerprint='fp6',
            name='AG6',
            labels={'app': 'app'},
            source='prometheus',
        )
        rule = SlackIntegrationRule.objects.create(
            name='rule',
            slack_channel='#chan',
            match_criteria={},
            message_template='Service is down at fe80::1ff:fe23:4567:890a.',
        )

        process_slack_for_alert_group(alert_group.id, rule.id)

        mock_service.send_notification.assert_called_once_with('#chan', 'Service is down at IP.')

    @patch('integrations.tasks.metrics_manager')
    @patch('integrations.tasks.SlackService')
    @patch('integrations.tasks.process_slack_for_alert_group.retry', side_effect=Retry('boom'))
    def test_process_slack_for_alert_group_increments_metric_on_retry(self, retry_mock, mock_service_cls, metrics_mock):
        mock_service = mock_service_cls.return_value
        mock_service.send_notification.side_effect = SlackNotificationError("network")

        alert_group = AlertGroup.objects.create(
            fingerprint='fp7',
            name='AG7',
            labels={'app': 'app'},
            source='prometheus',
        )
        rule = SlackIntegrationRule.objects.create(
            name='rule',
            slack_channel='#chan',
            match_criteria={},
            message_template='hi',
        )

        with self.assertRaises(Retry):
            process_slack_for_alert_group(alert_group.id, rule.id)

        metrics_mock.inc_counter.assert_called_once_with("sentryhub_slack_notifications_total", {"status": "retry"})


class SanitizeIpAddressesTests(TestCase):
    def test_sanitizes_ipv4_and_port(self):
        text = 'Alert on 192.168.1.10:9100 is firing.'
        self.assertEqual(sanitize_ip_addresses(text), 'Alert on IP is firing.')

    def test_sanitizes_ipv6(self):
        text = 'Service down at fe80::1ff:fe23:4567:890a.'
        self.assertEqual(sanitize_ip_addresses(text), 'Service down at IP.')
