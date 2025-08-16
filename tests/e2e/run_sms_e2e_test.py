# tests/e2e/run_sms_e2e_test.py
import pika
import json
import time
import os
import sys
import requests

def setup_test_environment():
    """Sets up Django and creates necessary objects for the test."""
    print("--- [E2E SMS Test] Setting up Django environment...")
    os.environ['SMS_PROVIDER_SEND_URL'] = 'http://localhost:5001/sms/send'
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sentryHub.settings')
    import django
    django.setup()

    from integrations.models import SmsIntegrationRule, PhoneBook
    from alerts.models import AlertGroup

    print("--- [E2E SMS Test] Clearing previous test data...")
    SmsIntegrationRule.objects.all().delete()
    PhoneBook.objects.all().delete()
    AlertGroup.objects.filter(fingerprint__startswith="e2e_sms_").delete()
    try:
        requests.post("http://localhost:5001/clear")
    except requests.RequestException as e:
        print(f"Could not clear mock server state: {e}. Continuing anyway.")
    
    print("--- [E2E SMS Test] Creating PhoneBook entries...")
    PhoneBook.objects.create(name="e2e_user1", phone_number="111111")
    PhoneBook.objects.create(name="e2e_user2", phone_number="222222")

    print("--- [E2E SMS Test] Creating SmsIntegrationRule...")
    SmsIntegrationRule.objects.create(
        name="E2E Test Rule for SMS Annotations",
        is_active=True,
        priority=100,
        match_criteria={"labels__service": "e2e-sms-service"},
        use_sms_annotation=True,
        firing_template="FIRING: {{ summary }} on {{ alert_group.labels.instance }}",
        resolved_template="RESOLVED: {{ summary }} on {{ alert_group.labels.instance }}"
    )
    print("--- [E2E SMS Test] Test setup complete.")

def send_alert_to_rabbitmq(alert_payload):
    host = os.getenv("RABBITMQ_HOST", "localhost")
    port = int(os.getenv("RABBITMQ_PORT", 5672))
    queue_name = 'sentryhub_alerts_external'
    
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=host, port=port))
        channel = connection.channel()
        channel.queue_declare(queue=queue_name, durable=True)
        message_body = json.dumps(alert_payload)
        channel.basic_publish(exchange='', routing_key=queue_name, body=message_body)
        print(f"--- [E2E SMS Test] Sent alert to RabbitMQ: {message_body[:120]}...")
        connection.close()
    except pika.exceptions.AMQPConnectionError as e:
        print(f"❌ RabbitMQ connection failed: {e}")
        sys.exit(1)

def verify_results():
    print("\n--- [E2E SMS Test] Waiting for tasks to be processed (20 seconds)...")
    time.sleep(20)

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sentryHub.settings')
    import django
    django.setup()
    from alerts.models import AlertGroup

    print("--- [E2E SMS Test] Verifying database state...")
    try:
        alert_group = AlertGroup.objects.get(fingerprint="e2e_sms_fingerprint")
        assert alert_group.current_status == "resolved"
        assert alert_group.instances.count() == 3
        print("✅ Database verification successful.")
    except (AlertGroup.DoesNotExist, AssertionError) as e:
        print(f"❌ Database verification failed: {e}")
        sys.exit(1)

    print("--- [E2E SMS Test] Verifying external SMS integration...")
    try:
        response = requests.get("http://localhost:5001/check")
        response.raise_for_status()
        received_data = response.json()
        
        sms_messages = received_data.get("sms", [])
        
        assert len(sms_messages) == 2, f"Expected 2 SMS messages, received {len(sms_messages)}."
        print(f"✅ SMS verification: Received {len(sms_messages)} messages.")

        firing_msg = next((m for m in sms_messages if m['message'].startswith('FIRING')), None)
        assert firing_msg is not None, "FIRING SMS message not received."
        assert firing_msg['recipients'] == ['111111']
        print("✅ SMS verification: FIRING message correct.")

        resolved_msg = next((m for m in sms_messages if m['message'].startswith('RESOLVED')), None)
        assert resolved_msg is not None, "RESOLVED SMS message not received."
        assert resolved_msg['recipients'] == ['111111']
        print("✅ SMS verification: RESOLVED message with opt-in correct.")

        all_recipients = [r for msg in sms_messages for r in msg['recipients']]
        assert '222222' not in all_recipients, "SMS sent for resolved alert without 'resolve=true' flag."
        print("✅ SMS verification: No SMS sent without opt-in, as expected.")

    except (requests.RequestException, AssertionError, KeyError, StopIteration) as e:
        print(f"❌ External integration verification failed: {e}")
        if 'received_data' in locals():
            print("--- Mock Server Data ---\n" + json.dumps(received_data, indent=2))
        sys.exit(1)

if __name__ == '__main__':
    setup_test_environment()
    
    payload_firing = {"alerts": [{"status": "firing", "labels": {"alertname": "E2ESmsTest", "service": "e2e-sms-service"}, "annotations": {"summary": "Firing SMS Test", "sms": "e2e_user1"}, "startsAt": "2025-01-01T10:00:00Z", "fingerprint": "e2e_sms_fingerprint"}]}
    payload_resolved_opt_in = {"alerts": [{"status": "resolved", "labels": {"alertname": "E2ESmsTest", "service": "e2e-sms-service"}, "annotations": {"summary": "Resolved SMS Test (Opt-in)", "sms": "e2e_user1;resolve=true"}, "startsAt": "2025-01-01T10:00:00Z", "endsAt": "2025-01-01T10:05:00Z", "fingerprint": "e2e_sms_fingerprint"}]}
    payload_resolved_no_opt_in = {"alerts": [{"status": "resolved", "labels": {"alertname": "E2ESmsTest", "service": "e2e-sms-service"}, "annotations": {"summary": "Resolved SMS Test (No Opt-in)", "sms": "e2e_user2"}, "startsAt": "2025-01-01T10:00:00Z", "endsAt": "2025-01-01T10:10:00Z", "fingerprint": "e2e_sms_fingerprint"}]}
    
    send_alert_to_rabbitmq(payload_firing)
    time.sleep(1)
    send_alert_to_rabbitmq(payload_resolved_opt_in)
    time.sleep(1)
    send_alert_to_rabbitmq(payload_resolved_no_opt_in)
    
    verify_results()
    
    print("\n🎉 E2E Test for SMS Resolve Logic Passed Successfully! 🎉")
    sys.exit(0)