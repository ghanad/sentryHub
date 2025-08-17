import pika
import json
import time
import os
import sys
import requests


def setup_test_environment():
    """Sets up Django and creates necessary objects for SMS E2E test."""
    print("--- [E2E SMS Test] Setting up Django environment...")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sentryHub.settings")
    os.environ.setdefault("SMS_PROVIDER_SEND_URL", "http://localhost:5001/sms")
    os.environ.setdefault("SMS_PROVIDER_USERNAME", "user")
    os.environ.setdefault("SMS_PROVIDER_PASSWORD", "pass")
    os.environ.setdefault("SMS_PROVIDER_DOMAIN", "test")
    os.environ.setdefault("SMS_PROVIDER_SENDER", "1000")

    import django
    django.setup()

    from integrations.models import SmsIntegrationRule, PhoneBook

    SmsIntegrationRule.objects.all().delete()
    PhoneBook.objects.all().delete()

    PhoneBook.objects.create(name="ali", phone_number="+989111111111")
    PhoneBook.objects.create(name="reza", phone_number="+989222222222")
    PhoneBook.objects.create(name="sina", phone_number="+989333333333")

    print("--- [E2E SMS Test] Creating SmsIntegrationRules...")
    SmsIntegrationRule.objects.create(
        name="E2E SMS Rule Recipients",
        is_active=True,
        priority=100,
        match_criteria={"labels__service": "sms-basic"},
        recipients="ali",
        use_sms_annotation=False,
        firing_template="RuleA Firing {{ summary }}",
    )

    SmsIntegrationRule.objects.create(
        name="E2E SMS Rule Annotation",
        is_active=True,
        priority=50,
        match_criteria={"labels__severity": "critical"},
        use_sms_annotation=True,
        firing_template="RuleB Firing {{ summary }}",
        resolved_template="RuleB Resolved {{ summary }}",
    )
    print("--- [E2E SMS Test] Test rules created successfully.")


def send_alert_to_rabbitmq(alert_payload):
    host = os.getenv("RABBITMQ_HOST", "localhost")
    port = int(os.getenv("RABBITMQ_PORT", 5672))
    queue_name = 'sentryhub_alerts_external'

    connection = pika.BlockingConnection(pika.ConnectionParameters(host=host, port=port))
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)

    message_body = json.dumps(alert_payload)
    channel.basic_publish(exchange='', routing_key=queue_name, body=message_body)
    print(f"--- [E2E SMS Test] Sent alert to RabbitMQ: {message_body[:100]}...")
    connection.close()


def verify_results():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sentryHub.settings")
    import django
    django.setup()
    from alerts.models import AlertGroup

    print("--- [E2E SMS Test] Verifying database state...")
    time.sleep(15)

    try:
        ag_rule = AlertGroup.objects.get(fingerprint="sms_rule_fp")
        ag_no_resolve = AlertGroup.objects.get(fingerprint="sms_no_resolve_fp")
        ag_resolve = AlertGroup.objects.get(fingerprint="sms_resolve_fp")
        assert ag_rule.name == "SMSTestRuleRecipients"
        assert ag_no_resolve.name == "SMSTestAnnotationNoResolve"
        assert ag_resolve.name == "SMSTestAnnotationResolve"
        print("✅ Database verification successful: All AlertGroups created.")
    except (AlertGroup.DoesNotExist, AssertionError) as e:
        print(f"❌ Database verification failed: {e}")
        sys.exit(1)

    print("--- [E2E SMS Test] Verifying external integrations...")
    try:
        response = requests.get("http://localhost:5001/check")
        response.raise_for_status()
        received_data = response.json()

        sms_messages = received_data.get("sms", [])
        assert len(sms_messages) == 4, f"Expected 4 SMS messages, but received {len(sms_messages)}."
        print("✅ SMS verification: Received 4 messages as expected.")

        def find_message(messages, text):
            return next((m for m in messages if text in m.get("messages", [])), None)

        rule_msg = find_message(sms_messages, "RuleA Firing RuleA summary")
        assert rule_msg and rule_msg["recipients"] == ["+989111111111"], "RuleA message incorrect"

        no_resolve_msg = find_message(sms_messages, "RuleB Firing NoResolve summary")
        assert no_resolve_msg and set(no_resolve_msg["recipients"]) == {"+989222222222", "+989333333333"}, "NoResolve firing message incorrect"

        firing_resolve_msg = find_message(sms_messages, "RuleB Firing Resolve summary")
        resolved_msg = find_message(sms_messages, "RuleB Resolved Resolve summary")
        assert firing_resolve_msg and firing_resolve_msg["recipients"] == ["+989111111111"], "Resolve firing message incorrect"
        assert resolved_msg and resolved_msg["recipients"] == ["+989111111111"], "Resolve resolved message incorrect"

        print("✅ SMS verification: Message contents and recipients are correct.")
    except (requests.RequestException, AssertionError, KeyError, StopIteration) as e:
        print(f"❌ External integration verification failed: {e}")
        if 'received_data' in locals():
            print("--- Mock Server Data ---")
            print(json.dumps(received_data, indent=2))
            print("------------------------")
        sys.exit(1)


if __name__ == '__main__':
    setup_test_environment()

    payload_rule = {
        "alerts": [{
            "status": "firing",
            "labels": {"alertname": "SMSTestRuleRecipients", "severity": "warning", "service": "sms-basic"},
            "annotations": {"summary": "RuleA summary"},
            "startsAt": "2024-01-01T00:00:00Z",
            "endsAt": "0001-01-01T00:00:00Z",
            "fingerprint": "sms_rule_fp"
        }]
    }

    payload_annotation_no_resolve_firing = {
        "alerts": [{
            "status": "firing",
            "labels": {
                "alertname": "SMSTestAnnotationNoResolve",
                "severity": "critical",
                "service": "other",
            },
            "annotations": {"summary": "NoResolve summary", "sms": "reza,sina"},
            "startsAt": "2024-01-01T01:00:00Z",
            "endsAt": "0001-01-01T00:00:00Z",
            "fingerprint": "sms_no_resolve_fp"
        }]
    }

    payload_annotation_no_resolve_resolved = {
        "alerts": [{
            "status": "resolved",
            "labels": {
                "alertname": "SMSTestAnnotationNoResolve",
                "severity": "critical",
                "service": "other",
            },
            "annotations": {"summary": "NoResolve summary", "sms": "reza,sina"},
            "startsAt": "2024-01-01T02:00:00Z",
            "endsAt": "2024-01-01T03:00:00Z",
            "fingerprint": "sms_no_resolve_fp"
        }]
    }

    payload_annotation_resolve_firing = {
        "alerts": [{
            "status": "firing",
            "labels": {
                "alertname": "SMSTestAnnotationResolve",
                "severity": "critical",
                "service": "other",
            },
            "annotations": {"summary": "Resolve summary", "sms": "ali;resolve=true"},
            "startsAt": "2024-01-01T04:00:00Z",
            "endsAt": "0001-01-01T00:00:00Z",
            "fingerprint": "sms_resolve_fp"
        }]
    }

    payload_annotation_resolve_resolved = {
        "alerts": [{
            "status": "resolved",
            "labels": {
                "alertname": "SMSTestAnnotationResolve",
                "severity": "critical",
                "service": "other",
            },
            "annotations": {"summary": "Resolve summary", "sms": "ali;resolve=true"},
            "startsAt": "2024-01-01T05:00:00Z",
            "endsAt": "2024-01-01T06:00:00Z",
            "fingerprint": "sms_resolve_fp"
        }]
    }

    send_alert_to_rabbitmq(payload_rule)
    send_alert_to_rabbitmq(payload_annotation_no_resolve_firing)
    send_alert_to_rabbitmq(payload_annotation_no_resolve_resolved)
    send_alert_to_rabbitmq(payload_annotation_resolve_firing)
    send_alert_to_rabbitmq(payload_annotation_resolve_resolved)

    verify_results()

    print("\n🎉 SMS E2E Test Passed Successfully! 🎉")
    sys.exit(0)

