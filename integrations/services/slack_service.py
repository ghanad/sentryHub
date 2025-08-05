import logging
from django.conf import settings
import requests

logger = logging.getLogger(__name__)

class SlackService:
    """
    Service for sending plain-text messages to Slack via an internal proxy endpoint.
    Automatically normalizes channel names to start with '#' unless they appear to be a Slack channel/DM/group ID.
    Logs detailed info on both success and failures.
    """

    def __init__(self):
        self.endpoint = getattr(settings, "SLACK_INTERNAL_ENDPOINT", "")

    def send_notification(self, channel: str, message: str) -> bool:
        """
        Send text to a Slack channel via POST.
        Args:
          channel: slack channel name (e.g., 'general' or '#general') or channel ID ('C012ABC', 'G123XYZ', etc.).
          message: plain text to send.

        Returns:
          True if the message was posted successfully ("200 OK" + body “ok”). False otherwise.
        """
        if not self.endpoint:
            logger.error("SlackService: SLACK_INTERNAL_ENDPOINT is not configured.")
            return False

        channel_fixed = self._normalize_channel(channel)
        payload = {"channel": channel_fixed, "text": message}

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
                return False

            # Success: log informational message
            logger.info(
                "Message posted to Slack channel %r: %r",
                channel_fixed,
                message[:200] + ("…" if len(message) > 200 else ""),  # Truncate long messages
            )
            return True

        except requests.exceptions.RequestException as exc:
            logger.error(
                "SlackService: HTTP request failed (channel=%r): %s",
                channel_fixed,
                exc,
                exc_info=True,
            )
            return False
        except Exception as exc:
            logger.error(
                "SlackService: unexpected error when sending to Slack (channel=%r): %s",
                channel_fixed,
                exc,
                exc_info=True,
            )
            return False

    def _normalize_channel(self, channel: str) -> str:
        """
        If the channel doesn't start with '#', and doesn't appear
        to be a Slack channel/group/DM/user ID, prefix it with '#'.
        Accepted ID prefixes: 'C', 'G', 'U', 'D'.
        """
        if not channel:
            return channel

        ch = channel.strip()
        if ch.startswith("#") or ch[0] in {"C", "G", "U", "D"}:
            return ch
        return f"#{ch}"
