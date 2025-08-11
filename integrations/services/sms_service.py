import logging
from django.conf import settings
import requests

from integrations.exceptions import SmsNotificationError

logger = logging.getLogger(__name__)


class SmsService:
    """Service responsible for sending SMS messages via external provider."""

    def __init__(self):
        self.endpoint = getattr(settings, "SMS_INTERNAL_ENDPOINT", "")

    def send_sms(self, phone_number: str, message: str) -> bool:
        if not self.endpoint:
            logger.error("SmsService: SMS_INTERNAL_ENDPOINT not configured.")
            return False

        payload = {"to": phone_number, "message": message}
        try:
            resp = requests.post(self.endpoint, json=payload, timeout=10)
            resp.raise_for_status()
            logger.info("SMS sent to %s", phone_number)
            return True
        except requests.exceptions.RequestException as exc:
            logger.warning("SmsService: network error sending SMS to %s: %s", phone_number, exc)
            raise SmsNotificationError("Network error during SMS send") from exc
