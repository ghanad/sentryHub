from django.test import TestCase
from unittest.mock import patch

from alerts.models import AlertGroup
from integrations.models import SlackIntegrationRule
from integrations.services.slack_matcher import SlackRuleMatcherService
from integrations.tasks import process_slack_for_alert_group


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
