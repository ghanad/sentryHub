import logging
from django.conf import settings
import requests

from integrations.exceptions import SmsNotificationError

logger = logging.getLogger(__name__)


class SmsService:
    """Service responsible for sending SMS messages via external provider."""

    def __init__(self):
        self.endpoint = getattr(settings, "SMS_INTERNAL_ENDPOINT", "")
        self.balance_url = getattr(settings, "SMS_PROVIDER_BALANCE_URL", "")
        self.username = getattr(settings, "SMS_PROVIDER_USERNAME", "")
        self.password = getattr(settings, "SMS_PROVIDER_PASSWORD", "")
        self.domain = getattr(settings, "SMS_PROVIDER_DOMAIN", "")

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

    def get_balance(self):
        if not all([self.balance_url, self.username, self.password, self.domain]):
            logger.error("SmsService: balance endpoint or credentials not configured.")
            return None

        headers = {"accept": "application/json", "cache-control": "no-cache"}
        try:
            resp = requests.get(
                self.balance_url,
                headers=headers,
                auth=(f"{self.username}/{self.domain}", self.password),
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                return data.get("credit", data)
            return data
        except requests.exceptions.RequestException as exc:
            logger.warning("SmsService: error fetching balance: %s", exc)
            return None
