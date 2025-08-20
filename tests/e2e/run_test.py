# tests/e2e/run_test.py
import pika
import json
import time
import os
import sys
import requests

SLACK_DELIVERY_METHOD = os.getenv("SLACK_DELIVERY_METHOD", "WEBHOOK").upper()


def purge_slack_queue():
    """Clear existing messages in the Slack RabbitMQ queue."""
    host = os.getenv("RABBITMQ_FORWARDER_HOST", "localhost")
    port = int(os.getenv("RABBITMQ_FORWARDER_PORT", 5672))
    queue_name = os.getenv("RABBITMQ_SLACK_QUEUE", "slack_notifications_queue")

    connection = pika.BlockingConnection(pika.ConnectionParameters(host=host, port=port))
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)
    channel.queue_purge(queue=queue_name)
    connection.close()
    print("--- [E2E Test] Purged Slack queue.")

def setup_test_environment():
    """Sets up Django and creates necessary objects for the test."""
    print("--- [E2E Test] Setting up Django environment...")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sentryHub.settings")
    os.environ["SLACK_DELIVERY_METHOD"] = SLACK_DELIVERY_METHOD
    import django
    django.setup()

    from integrations.models import SlackIntegrationRule

    # Clean slate for the test
    SlackIntegrationRule.objects.all().delete()

    # --- SCENARIO 1: Rule with a specific channel ---
    print("--- [E2E Test] Creating a specific SlackIntegrationRule (with channel)...")
    SlackIntegrationRule.objects.create(
        name="E2E Test Rule for Specific Channel",
        is_active=True,
        priority=100,
        match_criteria={"labels__service": "e2e-specific-service"},
        slack_channel="#specific-channel",
        message_template="Specific Rule Alert | Summary: {{ summary }} | Desc: {{ description }}"
    )

    # --- SCENARIO 2: Generic rule that uses the alert's label for channel ---
    print("--- [E2E Test] Creating a generic SlackIntegrationRule (without channel)...")
    SlackIntegrationRule.objects.create(
        name="E2E Test Rule for Label-based Channel",
        is_active=True,
        priority=50, # Lower priority than the specific one
        match_criteria={"labels__severity": "critical"}, # A generic match
        slack_channel="", # IMPORTANT: This must be empty
        message_template="Label-based Channel Alert | Summary: {{ summary }} | Desc: {{ description }}"
    )
    print("--- [E2E Test] Test rules created successfully.")

def send_alert_to_rabbitmq(alert_payload):
    host = os.getenv("RABBITMQ_HOST", "localhost")
    port = int(os.getenv("RABBITMQ_PORT", 5672))
    queue_name = 'sentryhub_alerts_external'
    
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=host, port=port))
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)
    
    message_body = json.dumps(alert_payload)
    channel.basic_publish(exchange='', routing_key=queue_name, body=message_body)
    print(f"--- [E2E Test] Sent alert to RabbitMQ: {message_body[:100]}...")
    connection.close()

def verify_slack_webhook(received_data):
    slack_messages = received_data.get("slack", [])
    assert len(slack_messages) == 2, f"Expected 2 Slack messages, but received {len(slack_messages)}."
    print("✅ Slack verification: Received 2 messages as expected.")

    specific_msg = next((m for m in slack_messages if m["channel"] == "#specific-channel"), None)
    assert specific_msg is not None, "Message for the specific rule was not received."
    expected_specific_text = (
        "Specific Rule Alert | Summary: Test for specific channel rule on IP. | "
        "Desc: This is the description for the SPECIFIC rule."
    )
    assert specific_msg["text"] == expected_specific_text, (
        f"Specific rule message content is incorrect. Got: '{specific_msg['text']}'"
    )
    print("✅ Slack verification: Message for specific rule is correct (IP sanitized).")

    label_msg = next((m for m in slack_messages if m["channel"] == "#dynamic-alerts-from-label"), None)
    assert label_msg is not None, "Message for the label-based rule was not received."
    expected_label_text = (
        "Label-based Channel Alert | Summary: Test for label-based channel. | "
        "Desc: This is the description for the LABEL-BASED rule on instance IP."
    )
    assert label_msg["text"] == expected_label_text, (
        f"Label-based rule message content is incorrect. Got: '{label_msg['text']}'"
    )
    print("✅ Slack verification: Message for label-based rule is correct (IP with port sanitized).")


def verify_slack_rabbitmq():
    print("--- [E2E Test] Verifying Slack messages in RabbitMQ...")
    host = os.getenv("RABBITMQ_FORWARDER_HOST", "localhost")
    port = int(os.getenv("RABBITMQ_FORWARDER_PORT", 5672))
    queue_name = os.getenv("RABBITMQ_SLACK_QUEUE", "slack_notifications_queue")
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=host, port=port))
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)

    messages = []
    start = time.time()
    while len(messages) < 2 and time.time() - start < 30:
        method_frame, _, body = channel.basic_get(queue=queue_name, auto_ack=True)
        if method_frame:
            messages.append(json.loads(body.decode()))
        else:
            time.sleep(1)
    connection.close()

    if len(messages) != 2:
        print(f"❌ Slack verification failed: expected 2 messages, received {len(messages)}.")
        sys.exit(1)
    print("✅ Slack RabbitMQ verification: Received 2 messages as expected.")

    specific_msg = next((m for m in messages if m["channel"] == "#specific-channel"), None)
    if specific_msg is None:
        print("❌ Slack verification failed: specific rule message not found.")
        sys.exit(1)
    expected_specific = (
        "Specific Rule Alert | Summary: Test for specific channel rule on 172.16.0.10. | "
        "Desc: This is the description for the SPECIFIC rule."
    )
    if specific_msg["text"] != expected_specific:
        print("❌ Slack verification failed: specific rule message content is incorrect.")
        sys.exit(1)

    label_msg = next((m for m in messages if m["channel"] == "#dynamic-alerts-from-label"), None)
    if label_msg is None:
        print("❌ Slack verification failed: label-based rule message not found.")
        sys.exit(1)
    expected_label = (
        "Label-based Channel Alert | Summary: Test for label-based channel. | "
        "Desc: This is the description for the LABEL-BASED rule on instance 192.168.1.1:8080."
    )
    if label_msg["text"] != expected_label:
        print("❌ Slack verification failed: label-based rule message content is incorrect.")
        sys.exit(1)

    print("✅ Slack RabbitMQ verification: Message contents are correct.")


def verify_results():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sentryHub.settings")
    import django
    django.setup()
    from alerts.models import AlertGroup

    print("--- [E2E Test] Verifying database state...")
    time.sleep(15)

    try:
        ag_specific = AlertGroup.objects.get(fingerprint="e2e_fingerprint_specific")
        ag_label = AlertGroup.objects.get(fingerprint="e2e_fingerprint_label")
        assert ag_specific.name == "E2ESpecificTest"
        assert ag_label.name == "E2ELabelTest"
        print("✅ Database verification successful: Both AlertGroups created.")
    except (AlertGroup.DoesNotExist, AssertionError) as e:
        print(f"❌ Database verification failed: {e}")
        sys.exit(1)

    if SLACK_DELIVERY_METHOD == "RABBITMQ":
        verify_slack_rabbitmq()
    else:
        print("--- [E2E Test] Verifying external integrations...")
        try:
            response = requests.get("http://localhost:5001/check")
            response.raise_for_status()
            received_data = response.json()
            verify_slack_webhook(received_data)
        except (requests.RequestException, AssertionError, KeyError, StopIteration) as e:
            print(f"❌ External integration verification failed: {e}")
            if 'received_data' in locals():
                print("--- Mock Server Data ---")
                print(json.dumps(received_data, indent=2))
                print("------------------------")
            sys.exit(1)

if __name__ == '__main__':
    if SLACK_DELIVERY_METHOD == 'RABBITMQ':
        purge_slack_queue()
    setup_test_environment()

    # --- MODIFIED: Added IP addresses to annotations ---
    # Payload 1: Should match the specific rule
    payload_specific = {
        "alerts": [{
            "status": "firing",
            "labels": { "alertname": "E2ESpecificTest", "severity": "warning", "service": "e2e-specific-service" },
            "annotations": { 
                "summary": "Test for specific channel rule on 172.16.0.10.",
                "description": "This is the description for the SPECIFIC rule." 
            },
            "startsAt": "2024-01-01T00:00:00Z", "endsAt": "0001-01-01T00:00:00Z",
            "fingerprint": "e2e_fingerprint_specific"
        }]
    }

    # Payload 2: Should match the generic rule and use the 'channel' label
    payload_label_based = {
        "alerts": [{
            "status": "firing",
            "labels": { 
                "alertname": "E2ELabelTest", 
                "severity": "critical", 
                "service": "other-service",
                "channel": "dynamic-alerts-from-label"
            },
            "annotations": { 
                "summary": "Test for label-based channel.",
                "description": "This is the description for the LABEL-BASED rule on instance 192.168.1.1:8080."
            },
            "startsAt": "2024-01-01T01:00:00Z", "endsAt": "0001-01-01T00:00:00Z",
            "fingerprint": "e2e_fingerprint_label"
        }]
    }
    
    send_alert_to_rabbitmq(payload_specific)
    send_alert_to_rabbitmq(payload_label_based)

    verify_results()

    print("\n🎉 E2E Test Passed Successfully! 🎉")
    sys.exit(0)