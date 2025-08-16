# tests/e2e/run_test.py
import pika
import json
import time
import os
import sys
import requests

def setup_test_environment():
    """Sets up Django and creates necessary objects for the test."""
    print("--- [E2E Test] Setting up Django environment...")
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sentryHub.settings')
    import django
    django.setup()

    from integrations.models import SlackIntegrationRule, SmsIntegrationRule, PhoneBook

    # Clean slate for the test
    SlackIntegrationRule.objects.all().delete()
    SmsIntegrationRule.objects.all().delete()
    PhoneBook.objects.all().delete()

    # --- SCENARIO 1: Slack Rule with a specific channel ---
    print("--- [E2E Test] Creating a specific SlackIntegrationRule (with channel)...")
    SlackIntegrationRule.objects.create(
        name="E2E Test Rule for Specific Channel",
        is_active=True,
        priority=100,
        match_criteria={"labels__service": "e2e-specific-service"},
        slack_channel="#specific-channel",
        message_template="Specific Rule Alert | Summary: {{ summary }} | Desc: {{ description }}"
    )

    # --- SCENARIO 2: Generic Slack rule that uses the alert's label for channel ---
    print("--- [E2E Test] Creating a generic SlackIntegrationRule (without channel)...")
    SlackIntegrationRule.objects.create(
        name="E2E Test Rule for Label-based Channel",
        is_active=True,
        priority=50,
        match_criteria={"labels__severity": "critical"},
        slack_channel="",
        message_template="Label-based Channel Alert | Summary: {{ summary }} | Desc: {{ description }}"
    )
    
    # --- SCENARIO 3: SMS PhoneBook entries ---
    print("--- [E2E Test] Creating PhoneBook entries for SMS tests...")
    PhoneBook.objects.create(name="sms_user1", phone_number="1111")
    PhoneBook.objects.create(name="sms_user2", phone_number="2222")

    # --- SCENARIO 4: SMS Rule using annotations ---
    print("--- [E2E Test] Creating SMS rule for annotation-based recipients...")
    SmsIntegrationRule.objects.create(
        name="E2E SMS Annotation Rule",
        is_active=True,
        priority=100,
        match_criteria={"labels__service": "e2e-sms-annotation"},
        use_sms_annotation=True,
        firing_template="Firing SMS for {{ alert_group.name }} to {{ alert_group.labels.sms_recipient }}.",
        resolved_template="Resolved SMS for {{ alert_group.name }}."
    )

    # --- SCENARIO 5: SMS Rule using rule-based recipients (no resolved message) ---
    print("--- [E2E Test] Creating SMS rule for rule-based recipients...")
    SmsIntegrationRule.objects.create(
        name="E2E SMS Rule-Based",
        is_active=True,
        priority=90,
        match_criteria={"labels__service": "e2e-sms-rule"},
        recipients="sms_user2",
        use_sms_annotation=False,
        firing_template="Rule-based firing SMS for {{ alert_group.name }}.",
        resolved_template="" # No resolved message
    )

    print("--- [E2E Test] Test environment setup complete.")


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

def verify_results():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sentryHub.settings')
    import django
    django.setup()
    from alerts.models import AlertGroup

    # 1. Verify Database State
    print("--- [E2E Test] Verifying database state...")
    time.sleep(15)

    try:
        # Check Slack alerts were created
        AlertGroup.objects.get(fingerprint="e2e_fingerprint_specific")
        AlertGroup.objects.get(fingerprint="e2e_fingerprint_label")
        # Check SMS alerts were created
        AlertGroup.objects.get(fingerprint="e2e_sms_fp_1")
        AlertGroup.objects.get(fingerprint="e2e_sms_fp_2")
        print("✅ Database verification successful: All 4 AlertGroups created.")
    except (AlertGroup.DoesNotExist, AssertionError) as e:
        print(f"❌ Database verification failed: {e}")
        sys.exit(1)

    # 2. Verify External Integrations (via mock server)
    print("--- [E2E Test] Verifying external integrations...")
    try:
        response = requests.get("http://localhost:5001/check")
        response.raise_for_status()
        received_data = response.json()
        
        # Verify Slack messages
        slack_messages = received_data.get("slack", [])
        assert len(slack_messages) == 2, f"Expected 2 Slack messages, but received {len(slack_messages)}."
        print("✅ Slack verification: Received 2 messages as expected.")
        
        specific_msg = next((m for m in slack_messages if m['channel'] == '#specific-channel'), None)
        assert specific_msg is not None, "Message for the specific Slack rule was not received."
        expected_specific_text = "Specific Rule Alert | Summary: Test for specific channel rule on IP. | Desc: This is the description for the SPECIFIC rule."
        assert specific_msg['text'] == expected_specific_text
        print("✅ Slack verification: Message for specific rule is correct.")

        label_msg = next((m for m in slack_messages if m['channel'] == '#dynamic-alerts-from-label'), None)
        assert label_msg is not None, "Message for the label-based Slack rule was not received."
        expected_label_text = "Label-based Channel Alert | Summary: Test for label-based channel. | Desc: This is the description for the LABEL-BASED rule on instance IP."
        assert label_msg['text'] == expected_label_text
        print("✅ Slack verification: Message for label-based rule is correct.")

        # Verify SMS messages
        sms_messages = received_data.get("sms", [])
        assert len(sms_messages) == 3, f"Expected 3 SMS messages, but received {len(sms_messages)}."
        print("✅ SMS verification: Received 3 messages as expected.")

        # Check SMS 1: Annotation-based firing
        sms1 = next((m for m in sms_messages if "Firing SMS for E2ESMSAnnotationTest" in m['messages'][0]), None)
        assert sms1 is not None, "SMS for annotation-based firing not found."
        assert sms1['recipients'] == ['1111']
        assert sms1['messages'][0] == "Firing SMS for E2ESMSAnnotationTest to sms_user1."
        print("✅ SMS verification: Message #1 (annotation firing) is correct.")

        # Check SMS 2: Annotation-based resolved
        sms2 = next((m for m in sms_messages if "Resolved SMS for E2ESMSAnnotationTest" in m['messages'][0]), None)
        assert sms2 is not None, "SMS for annotation-based resolved not found."
        assert sms2['recipients'] == ['1111']
        assert sms2['messages'][0] == "Resolved SMS for E2ESMSAnnotationTest."
        print("✅ SMS verification: Message #2 (annotation resolved) is correct.")

        # Check SMS 3: Rule-based firing
        sms3 = next((m for m in sms_messages if "Rule-based firing SMS for E2ESMSRuleTest" in m['messages'][0]), None)
        assert sms3 is not None, "SMS for rule-based firing not found."
        assert sms3['recipients'] == ['2222']
        assert sms3['messages'][0] == "Rule-based firing SMS for E2ESMSRuleTest."
        print("✅ SMS verification: Message #3 (rule-based firing) is correct.")

    except (requests.RequestException, AssertionError, KeyError, StopIteration) as e:
        print(f"❌ External integration verification failed: {e}")
        if 'received_data' in locals():
            print("--- Mock Server Data ---")
            print(json.dumps(received_data, indent=2))
            print("------------------------")
        sys.exit(1)

if __name__ == '__main__':
    setup_test_environment()

    # --- Slack Payloads ---
    payload_specific = {
        "alerts": [{"status": "firing", "labels": { "alertname": "E2ESpecificTest", "severity": "warning", "service": "e2e-specific-service" }, "annotations": { "summary": "Test for specific channel rule on 172.16.0.10.", "description": "This is the description for the SPECIFIC rule." }, "startsAt": "2024-01-01T00:00:00Z", "endsAt": "0001-01-01T00:00:00Z", "fingerprint": "e2e_fingerprint_specific"}]
    }
    payload_label_based = {
        "alerts": [{"status": "firing", "labels": { "alertname": "E2ELabelTest", "severity": "critical", "service": "other-service", "channel": "dynamic-alerts-from-label" }, "annotations": { "summary": "Test for label-based channel.", "description": "This is the description for the LABEL-BASED rule on instance 192.168.1.1:8080." }, "startsAt": "2024-01-01T01:00:00Z", "endsAt": "0001-01-01T00:00:00Z", "fingerprint": "e2e_fingerprint_label"}]
    }

    # --- SMS Payloads ---
    payload_sms_annotation_firing = {
        "alerts": [{"status": "firing", "labels": { "alertname": "E2ESMSAnnotationTest", "service": "e2e-sms-annotation", "sms_recipient": "sms_user1" }, "annotations": { "sms": "sms_user1" }, "startsAt": "2024-01-02T00:00:00Z", "endsAt": "0001-01-01T00:00:00Z", "fingerprint": "e2e_sms_fp_1"}]
    }
    payload_sms_annotation_resolved = {
        "alerts": [{"status": "resolved", "labels": { "alertname": "E2ESMSAnnotationTest", "service": "e2e-sms-annotation", "sms_recipient": "sms_user1" }, "annotations": { "sms": "sms_user1" }, "startsAt": "2024-01-02T00:00:00Z", "endsAt": "2024-01-02T01:00:00Z", "fingerprint": "e2e_sms_fp_1"}]
    }
    payload_sms_rule_firing = {
        "alerts": [{"status": "firing", "labels": { "alertname": "E2ESMSRuleTest", "service": "e2e-sms-rule" }, "annotations": {}, "startsAt": "2024-01-03T00:00:00Z", "endsAt": "0001-01-01T00:00:00Z", "fingerprint": "e2e_sms_fp_2"}]
    }
    payload_sms_rule_resolved = {
        "alerts": [{"status": "resolved", "labels": { "alertname": "E2ESMSRuleTest", "service": "e2e-sms-rule" }, "annotations": {}, "startsAt": "2024-01-03T00:00:00Z", "endsAt": "2024-01-03T01:00:00Z", "fingerprint": "e2e_sms_fp_2"}]
    }
    
    send_alert_to_rabbitmq(payload_specific)
    send_alert_to_rabbitmq(payload_label_based)
    send_alert_to_rabbitmq(payload_sms_annotation_firing)
    send_alert_to_rabbitmq(payload_sms_annotation_resolved)
    send_alert_to_rabbitmq(payload_sms_rule_firing)
    send_alert_to_rabbitmq(payload_sms_rule_resolved)
    
    verify_results()
    
    print("\n🎉 E2E Test Passed Successfully! 🎉")
    sys.exit(0)