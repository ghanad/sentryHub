from django.test import SimpleTestCase, override_settings
from unittest.mock import Mock, patch
import json

from integrations.services.sms_service import SmsService


class SmsServiceSendBulkTests(SimpleTestCase):
    @override_settings(
        SMS_PROVIDER_SEND_URL="http://sms",
        SMS_PROVIDER_USERNAME="u",
        SMS_PROVIDER_PASSWORD="p",
        SMS_PROVIDER_DOMAIN="d",
        SMS_PROVIDER_SENDER="s",
    )
    def test_send_bulk_via_http_success(self):
        service = SmsService()
        response_mock = Mock(status_code=200)
        response_mock.raise_for_status = Mock()
        response_mock.json = Mock(return_value={"messages": [{"status": 1}]})
        with patch(
            "integrations.services.sms_service.requests.post",
            return_value=response_mock,
        ) as post_mock:
            result = service.send_bulk(["0912"], "hi")
        self.assertEqual(result, {"messages": [{"status": 1}]})
        post_mock.assert_called_once()

    @override_settings(
        SMS_DELIVERY_METHOD="RABBITMQ",
        RABBITMQ_SMS_FORWARDER_CONFIG={
            "HOST": "localhost",
            "PORT": 5672,
            "USER": "guest",
            "PASSWORD": "guest",
            "QUEUE_NAME": "sms_notifications_queue",
        },
    )
    @patch("integrations.services.sms_service.pika.BasicProperties")
    @patch("integrations.services.sms_service.pika.BlockingConnection")
    def test_send_bulk_rabbitmq_success(self, connection_mock, basic_props_mock):
        service = SmsService()
        channel_mock = Mock()
        connection_instance = Mock()
        connection_instance.channel.return_value = channel_mock
        connection_mock.return_value = connection_instance
        basic_props_mock.return_value = Mock()

        result = service.send_bulk(["0912"], "hi")

        self.assertTrue(result)
        connection_mock.assert_called_once()
        channel_mock.queue_declare.assert_called_once_with(queue="sms_notifications_queue", durable=True)
        channel_mock.basic_publish.assert_called_once()
        args, kwargs = channel_mock.basic_publish.call_args
        self.assertEqual(kwargs["routing_key"], "sms_notifications_queue")
        self.assertEqual(json.loads(kwargs["body"]), {"recipients": ["0912"], "text": "hi"})
        self.assertIs(kwargs["properties"], basic_props_mock.return_value)
        connection_instance.close.assert_called_once()
