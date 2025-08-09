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
    ... (docstring) ...
    """

    def __init__(self):
        self.endpoint = getattr(settings, "SLACK_INTERNAL_ENDPOINT", "")

    def send_notification(self, channel: str, message: str) -> bool:
        """
        Send text to a Slack channel via POST.
        ... (docstring) ...
        """
        if not self.endpoint:
            logger.error("SlackService: SLACK_INTERNAL_ENDPOINT is not configured.")
            metrics_manager.inc_counter(
                "sentryhub_component_initialization_errors_total",
                labels={"component": "slack"},
            )
            return False

        channel_fixed = self._normalize_channel(channel)
        payload = {"channel": channel_fixed, "text": message}

        max_retries = 3
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
                        "SlackService: send failed (channel=%r): %s",
                        channel_fixed,
                        error_msg,
                        exc_info=True,
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

                # --- MODIFIED/FIXED LINE HERE ---
                metrics_manager.set_gauge(
                    "sentryhub_component_last_successful_api_call_timestamp",
                    value=time.time(),
                    labels={"component": "slack"},
                )
                # --- END OF MODIFIED LINE ---

                return True

            except requests.exceptions.RequestException as exc:
                logger.warning(
                    "SlackService: HTTP request attempt %d/%d failed (channel=%r): %s",
                    attempt,
                    max_retries,
                    channel_fixed,
                    exc,
                    exc_info=True,
                )
                if attempt == max_retries:
                    metrics_manager.inc_counter(
                        "sentryhub_slack_notifications_total",
                        labels={"status": "failure", "reason": "network_error"},
                    )
                    raise SlackNotificationError(
                        "Network error during Slack notification"
                    ) from exc
                time.sleep(2 ** (attempt - 1))
            except Exception as exc:
                logger.error(
                    "SlackService: unexpected error when sending to Slack (channel=%r): %s",
                    channel_fixed,
                    exc,
                    exc_info=True,
                )
                metrics_manager.inc_counter(
                    "sentryhub_slack_notifications_total",
                    labels={"status": "failure", "reason": "unexpected"},
                )
                return False

    def _normalize_channel(self, channel: str) -> str:
        if not channel:
            return channel

        ch = channel.strip()
        if not ch:  # Handle empty string after stripping
            return ""

        if ch.startswith("#") or ch[0] in {"C", "G", "U", "D"}:
            return ch
        return f"#{ch}"
