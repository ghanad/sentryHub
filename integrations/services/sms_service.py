import logging
import json
from typing import List, Optional, Dict, Any

from django.conf import settings
import requests
import pika

from integrations.exceptions import SmsNotificationError

logger = logging.getLogger(__name__)


class SmsService:
    """Service responsible for sending SMS messages via external provider."""

    # Provider status codes mapped to human-readable English messages.
    STATUS_MESSAGES = {
        0: "Sent successfully",
        1: "Invalid recipient number",
        2: "Invalid sender number",
        3: "Invalid encoding parameter (ensure the message matches the selected encoding)",
        4: "Invalid mclass parameter",
        6: "Invalid UDH parameter",
        8: "Send time is outside the allowed promotional SMS window (07:00 to 22:00)",
        13: "Message content (UDH and text) is empty (recheck message text and UDH parameter)",
        14: "Insufficient credit balance to send the message",
        15: "Provider server was resolving an internal issue during send (retry the request)",
        16: "Account is inactive (contact the sales team)",
        17: "Account has expired (contact the sales team)",
        18: "Invalid username or password (verify credentials)",
        19: "Invalid request (username, password, and domain combination is incorrect; contact sales for new credentials)",
        20: "Sender number does not belong to the account",
        22: "Service is not enabled for the account",
        23: "Provider cannot process a new request at the moment (retry the request)",
        24: "Invalid message ID (may be incorrect or older than one day)",
        25: "Invalid method name (verify against the provider documentation)",
        27: "Recipient number is blacklisted by the operator (cannot receive promotional SMS)",
        28: "Recipient number is currently blocked by Magfa based on its prefix",
        29: "Source IP address is not permitted to access this service",
        30: "Number of SMS parts exceeds the maximum allowed limit (265)",
        31: "Invalid JSON format in the request",
        33: "Recipient has blocked messages from this sender (unsubscribe code 11)",
        34: "No verified information exists for this number",
        35: "Message text contains an invalid character",
        101: "Length of messageBodies array does not match recipients array",
        102: "Length of messageClass array does not match recipients array",
        103: "Length of senderNumbers array does not match recipients array",
        104: "Length of udhs array does not match recipients array",
        105: "Length of priorities array does not match recipients array",
        106: "Recipients array is empty",
        107: "Recipients array length exceeds the maximum allowed",
        108: "Senders array is empty",
        109: "Length of encoding array does not match recipients array",
        110: "Length of checkingMessageIds array does not match recipients array",
    }

    def __init__(self):
        self.send_url = getattr(settings, "SMS_PROVIDER_SEND_URL", "")
        self.balance_url = getattr(settings, "SMS_PROVIDER_BALANCE_URL", "")
        self.username = getattr(settings, "SMS_PROVIDER_USERNAME", "")
        self.password = getattr(settings, "SMS_PROVIDER_PASSWORD", "")
        self.domain = getattr(settings, "SMS_PROVIDER_DOMAIN", "")
        self.sender = getattr(settings, "SMS_PROVIDER_SENDER", "")

    def send_sms(self, phone_number: str, message: str, fingerprint: str = "N/A") -> Optional[Dict[str, Any]]:
        """Convenience wrapper for sending a single SMS."""
        return self.send_bulk([phone_number], message, fingerprint)

    def send_bulk(
        self, phone_numbers: List[str], message: str, fingerprint: str = "N/A"
    ) -> Optional[Dict[str, Any]]:
        """Send the same message to multiple recipients in a single request."""
        delivery_method = getattr(settings, "SMS_DELIVERY_METHOD", "HTTP").upper()
        if delivery_method == "RABBITMQ":
            return self._send_to_rabbitmq(phone_numbers, message, fingerprint)
        return self._send_via_http(phone_numbers, message, fingerprint)

    def _send_to_rabbitmq(
        self, phone_numbers: List[str], message: str, fingerprint: str
    ) -> bool:
        """Queues the SMS message in RabbitMQ."""
        config = settings.RABBITMQ_SMS_FORWARDER_CONFIG
        payload = json.dumps({"recipients": phone_numbers, "text": message})

        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=config["HOST"],
                    port=config["PORT"],
                    credentials=pika.PlainCredentials(config["USER"], config["PASSWORD"]),
                )
            )
            channel = connection.channel()
            channel.queue_declare(queue=config["QUEUE_NAME"], durable=True)

            channel.basic_publish(
                exchange="",
                routing_key=config["QUEUE_NAME"],
                body=payload,
                properties=pika.BasicProperties(delivery_mode=2),
            )

            connection.close()
            logger.info(
                "SmsService (FP: %s): Message queued successfully in RabbitMQ for recipients %s.",
                fingerprint,
                phone_numbers,
            )
            return True
        except Exception as e:  # pragma: no cover
            logger.error(
                "SmsService (FP: %s): Failed to queue message in RabbitMQ. Error: %s",
                fingerprint,
                e,
                exc_info=True,
            )
            return False

    def _send_via_http(
        self, phone_numbers: List[str], message: str, fingerprint: str
    ) -> Optional[Dict[str, Any]]:
        if not all([self.send_url, self.username, self.password, self.domain, self.sender]):
            logger.error(
                "SmsService (FP: %s): SMS provider send URL or credentials not configured.",
                fingerprint,
            )
            return None

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
            return resp_data
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
