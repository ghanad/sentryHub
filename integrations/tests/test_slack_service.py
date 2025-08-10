from django.test import SimpleTestCase, override_settings
from unittest.mock import Mock, patch
import requests

from integrations.services.slack_service import SlackService, SlackNotificationError


class SlackServiceNormalizeChannelTests(SimpleTestCase):
    def setUp(self):
        self.service = SlackService()

    def test_normalize_channel_behaviour_per_implementation(self):
        # Keeps channels that already start with '#'
        self.assertEqual(self.service._normalize_channel("#general"), "#general")
        # Adds '#' when no special prefix; trims whitespace
        self.assertEqual(self.service._normalize_channel("devops"), "#devops")
        self.assertEqual(self.service._normalize_channel("  devops  "), "#devops")
        # Leaves Slack-like IDs untouched
        self.assertEqual(self.service._normalize_channel("C123ABC"), "C123ABC")
        self.assertEqual(self.service._normalize_channel("G456DEF"), "G456DEF")
        self.assertEqual(self.service._normalize_channel("U789HIJ"), "U789HIJ")
        self.assertEqual(self.service._normalize_channel("D000XYZ"), "D000XYZ")
        # Does not strip '@' per current implementation; will prefix with '#'
        self.assertEqual(self.service._normalize_channel("@alerts"), "#@alerts")
        # Falsy input returns as-is (empty string)
        self.assertEqual(self.service._normalize_channel(""), "")
        # Whitespace-only input should now return an empty string
        self.assertEqual(self.service._normalize_channel("   "), "")


class SlackServiceSendNotificationTests(SimpleTestCase):
    @override_settings(SLACK_INTERNAL_ENDPOINT="http://slack")
    @patch("integrations.services.slack_service.metrics_manager")
    def test_send_notification_success(self, metrics_mock):
        service = SlackService()
        response_mock = Mock(status_code=200, text="ok")
        response_mock.raise_for_status = Mock()
        with patch(
            "integrations.services.slack_service.requests.post",
            return_value=response_mock,
        ) as post_mock:
            result = service.send_notification("#general", "hi")
        self.assertTrue(result)
        post_mock.assert_called_once()
        metrics_mock.inc_counter.assert_called()
        metrics_mock.set_gauge.assert_called()

    @override_settings(SLACK_INTERNAL_ENDPOINT="http://slack")
    @patch("integrations.services.slack_service.metrics_manager")
    def test_send_notification_bad_response(self, metrics_mock):
        service = SlackService()
        response_mock = Mock(status_code=200, text="error")
        response_mock.raise_for_status = Mock()
        with patch(
            "integrations.services.slack_service.requests.post",
            return_value=response_mock,
        ):
            result = service.send_notification("#general", "hi")
        self.assertFalse(result)
        metrics_mock.inc_counter.assert_called()

    @override_settings(SLACK_INTERNAL_ENDPOINT="http://slack")
    @patch("integrations.services.slack_service.metrics_manager")
    def test_send_notification_network_error_raises(self, metrics_mock):
        service = SlackService()
        with patch(
            "integrations.services.slack_service.requests.post",
            side_effect=requests.exceptions.RequestException,
        ) as post_mock:
            with patch("integrations.services.slack_service.time.sleep") as sleep_mock:
                with self.assertRaises(SlackNotificationError):
                    service.send_notification("#general", "hi")
        self.assertEqual(post_mock.call_count, 3)
        self.assertEqual(sleep_mock.call_count, 2)
        metrics_mock.inc_counter.assert_called()

    @override_settings(SLACK_INTERNAL_ENDPOINT="http://slack")
    @patch("integrations.services.slack_service.metrics_manager")
    def test_send_notification_retries_and_succeeds(self, metrics_mock):
        service = SlackService()
        response_mock = Mock(status_code=200, text="ok")
        response_mock.raise_for_status = Mock()
        side_effects = [
            requests.exceptions.RequestException,
            requests.exceptions.RequestException,
            response_mock,
        ]
        with patch(
            "integrations.services.slack_service.requests.post",
            side_effect=side_effects,
        ) as post_mock:
            with patch("integrations.services.slack_service.time.sleep") as sleep_mock:
                result = service.send_notification("#general", "hi")
        self.assertTrue(result)
        self.assertEqual(post_mock.call_count, 3)
        self.assertEqual(sleep_mock.call_count, 2)
        metrics_mock.inc_counter.assert_called()

    @override_settings(SLACK_INTERNAL_ENDPOINT="")
    @patch("integrations.services.slack_service.metrics_manager")
    def test_send_notification_no_endpoint(self, metrics_mock):
        service = SlackService()
        result = service.send_notification("#general", "hi")
        self.assertFalse(result)
        metrics_mock.inc_counter.assert_called()
