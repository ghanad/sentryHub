import logging
from typing import List

from django.conf import settings
import requests

from integrations.exceptions import SmsNotificationError

logger = logging.getLogger(__name__)


class SmsService:
    """Service responsible for sending SMS messages via external provider."""

    def __init__(self):
        self.send_url = getattr(settings, "SMS_PROVIDER_SEND_URL", "")
        self.balance_url = getattr(settings, "SMS_PROVIDER_BALANCE_URL", "")
        self.username = getattr(settings, "SMS_PROVIDER_USERNAME", "")
        self.password = getattr(settings, "SMS_PROVIDER_PASSWORD", "")
        self.domain = getattr(settings, "SMS_PROVIDER_DOMAIN", "")
        self.sender = getattr(settings, "SMS_PROVIDER_SENDER", "")

    def send_sms(self, phone_number: str, message: str, fingerprint: str = "N/A") -> bool:
        """Convenience wrapper for sending a single SMS."""
        return self.send_bulk([phone_number], message, fingerprint)

    def send_bulk(self, phone_numbers: List[str], message: str, fingerprint: str = "N/A") -> bool:
        """Send the same message to multiple recipients in a single request."""
        if not all([self.send_url, self.username, self.password, self.domain, self.sender]):
            logger.error(
                "SmsService (FP: %s): SMS provider send URL or credentials not configured.",
                fingerprint,
            )
            return False

        headers = {"accept": "application/json", "cache-control": "no-cache"}
        payload_json = {
            "senders": [self.sender] * len(phone_numbers),
            "messages": [message] * len(phone_numbers),
            "recipients": phone_numbers,
        }
        try:
            resp = requests.post(
                self.send_url,
                headers=headers,
                auth=(f"{self.username}/{self.domain}", self.password),
                json=payload_json,
                timeout=10,
            )
            resp.raise_for_status()
            try:
                resp_data = resp.json()
            except ValueError:
                resp_data = resp.text
            logger.info(
                "SmsService (FP: %s): provider response: %s",
                fingerprint,
                resp_data,
            )
            return True
        except requests.exceptions.RequestException as exc:
            logger.warning(
                "SmsService (FP: %s): network error sending SMS: %s", fingerprint, exc
            )
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
