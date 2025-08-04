import logging
from django.conf import settings
import requests

logger = logging.getLogger(__name__)


class SlackService:
    """Service for sending messages to Slack via internal proxy."""

    def __init__(self):
        self.endpoint = getattr(settings, "SLACK_INTERNAL_ENDPOINT", "")

    def send_notification(self, channel: str, message: str) -> bool:
        """Send a message to the given Slack channel."""
        if not self.endpoint:
            logger.error("SlackService: SLACK_INTERNAL_ENDPOINT is not configured.")
            return False
        payload = {"channel": channel, "text": message}
        try:
            response = requests.post(self.endpoint, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as exc:
            logger.error("SlackService: failed to send notification: %s", exc, exc_info=True)
            return False
