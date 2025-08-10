# integrations/services/slack_service.py

import logging
from django.conf import settings
import requests
import time

from core.services.metrics import metrics_manager
from integrations.exceptions import SlackNotificationError

logger = logging.getLogger(__name__)


class SlackService:
    """
    Service for sending plain-text messages to Slack via an internal proxy endpoint.
    Includes retry logic for network errors and adds contextual fingerprint to logs.
    """

    def __init__(self):
        self.endpoint = getattr(settings, "SLACK_INTERNAL_ENDPOINT", "")

    def send_notification(self, channel: str, message: str, fingerprint: str = "N/A") -> bool:
        """
        Send text to a Slack channel via POST. Retries on transient network errors.

        Args:
            channel (str): The target Slack channel (e.g., '#alerts', 'C12345').
            message (str): The plain text message to send.
            fingerprint (str, optional): The alert fingerprint for logging context. Defaults to "N/A".

        Returns:
            bool: True on success, False on failure.

        Raises:
            SlackNotificationError: If the notification fails after all retry attempts due to network issues.
        """
        if not self.endpoint:
            logger.error(f"SlackService (FP: {fingerprint}): SLACK_INTERNAL_ENDPOINT is not configured.")
            metrics_manager.inc_counter(
                "sentryhub_component_initialization_errors_total",
                labels={"component": "slack"},
            )
            return False

        channel_fixed = self._normalize_channel(channel)
        payload = {"channel": channel_fixed, "text": message}

        max_retries = 3
        timeout_exceptions = (requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout)

        for attempt in range(1, max_retries + 1):
            try:
                resp = requests.post(self.endpoint, json=payload, timeout=10)
                resp.raise_for_status()

                body = resp.text.strip().lower()
                if body != "ok":
                    error_msg = (
                        f"Slack returned unexpected response "
                        f"(status={resp.status_code}, body={resp.text!r})"
                    )
                    logger.error(
                        f"SlackService (FP: {fingerprint}): send failed (channel={channel_fixed!r}): {error_msg}"
                    )
                    metrics_manager.inc_counter(
                        "sentryhub_slack_notifications_total",
                        labels={"status": "failure", "reason": "bad_response"},
                    )
                    return False

                logger.info(
                    "Message posted to Slack channel %r: %r",
                    channel_fixed,
                    message[:200] + ("…" if len(message) > 200 else ""),
                )
                metrics_manager.inc_counter(
                    "sentryhub_slack_notifications_total", labels={"status": "success"}
                )
                metrics_manager.set_gauge(
                    "sentryhub_component_last_successful_api_call_timestamp",
                    value=time.time(),
                    labels={"component": "slack"},
                )
                return True

            except timeout_exceptions as exc:
                retry_delay = 2 ** (attempt - 1)
                logger.warning(
                    f"SlackService (FP: {fingerprint}): Timeout on attempt {attempt}/{max_retries} for channel {channel_fixed!r}. Retrying in {retry_delay}s... Error: {exc}"
                )
                if attempt == max_retries:
                    metrics_manager.inc_counter(
                        "sentryhub_slack_notifications_total",
                        labels={"status": "failure", "reason": "network_error"},
                    )
                    raise SlackNotificationError(
                        "Network error during Slack notification after multiple retries"
                    ) from exc
                time.sleep(retry_delay)

            except requests.exceptions.RequestException as exc:
                retry_delay = 2 ** (attempt - 1)
                logger.warning(
                    f"SlackService (FP: {fingerprint}): HTTP request attempt {attempt}/{max_retries} failed (channel={channel_fixed!r}): {exc}. Retrying in {retry_delay}s..."
                )
                if attempt == max_retries:
                    metrics_manager.inc_counter(
                        "sentryhub_slack_notifications_total",
                        labels={"status": "failure", "reason": "network_error"},
                    )
                    raise SlackNotificationError(
                        "Network error during Slack notification"
                    ) from exc
                time.sleep(retry_delay)

            except Exception as exc:
                logger.error(
                    f"SlackService (FP: {fingerprint}): unexpected error when sending to Slack (channel={channel_fixed!r}): {exc}",
                    exc_info=True,
                )
                metrics_manager.inc_counter(
                    "sentryhub_slack_notifications_total",
                    labels={"status": "failure", "reason": "unexpected"},
                )
                return False
        return False # Should not be reached, but as a fallback

    def _normalize_channel(self, channel: str) -> str:
        if not channel:
            return channel

        ch = channel.strip()
        if not ch:
            return ""

        if ch.startswith("#") or ch[0] in {"C", "G", "U", "D"}:
            return ch
        return f"#{ch}"