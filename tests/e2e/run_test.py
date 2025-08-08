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

    from integrations.models import SlackIntegrationRule

    # Delete any pre-existing rules to ensure a clean slate for the test
    SlackIntegrationRule.objects.all().delete()

    # Create a Slack rule that WILL match our test alert payload
    print("--- [E2E Test] Creating a matching SlackIntegrationRule...")
    SlackIntegrationRule.objects.create(
        name="E2E Test Rule for Slack",
        is_active=True,
        priority=100,
        # This criteria will match the payload sent by this script
        match_criteria={
            "labels__service": "e2e-service",
            "labels__severity": "critical"
        },
        slack_channel="#e2e-tests", # Channel sent to mock server
        message_template="E2E Test Alert: {{ alert_group.labels.alertname }} is firing!"
    )
    print("--- [E2E Test] Test rule created successfully.")

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
    # Django is already set up by setup_test_environment()
    from alerts.models import AlertGroup

    # 1. Verify Database State
    print("--- [E2E Test] Verifying database state...")
    time.sleep(15) # Wait for all background processes to complete

    try:
        alert_group = AlertGroup.objects.get(fingerprint="e2e_fingerprint_for_slack")
        assert alert_group.name == "E2ESlackTest"
        print("✅ Database verification successful: AlertGroup created correctly.")
    except AlertGroup.DoesNotExist:
        print("❌ Database verification failed: AlertGroup was not created.")
        sys.exit(1)
    except AssertionError as e:
        print(f"❌ Database verification failed: {e}")
        sys.exit(1)

    # 2. Verify External Integrations (via mock server)
    print("--- [E2E Test] Verifying external integrations...")
    try:
        response = requests.get("http://localhost:5001/check")
        response.raise_for_status()
        received_data = response.json()
        
        # Check Slack
        assert len(received_data["slack"]) > 0, "No message was sent to Slack."
        slack_message_payload = received_data["slack"][0]
        
        # Verify channel and message content
        assert slack_message_payload['channel'] == "#e2e-tests", f"Message sent to wrong channel: {slack_message_payload['channel']}"
        expected_text = "E2E Test Alert: E2ESlackTest is firing!"
        assert slack_message_payload['text'] == expected_text, f"Slack message content is incorrect: '{slack_message_payload['text']}'"
        print("✅ Slack verification successful: Message with correct content received by mock server.")

    except (requests.RequestException, AssertionError, KeyError) as e:
        print(f"❌ External integration verification failed: {e}")
        # Print the received data for debugging
        if 'received_data' in locals():
            print("--- Mock Server Data ---")
            print(json.dumps(received_data, indent=2))
            print("------------------------")
        sys.exit(1)

if __name__ == '__main__':
    # Step 1: Prepare the test environment and database records
    setup_test_environment()

    # Step 2: Define the payload that will be sent
    test_payload = {
        "alerts": [
            {
                "status": "firing",
                "labels": { 
                    "alertname": "E2ESlackTest", 
                    "severity": "critical", 
                    "service": "e2e-service"
                },
                "annotations": { "summary": "This is a full E2E test." },
                "startsAt": "2024-01-01T00:00:00Z",
                "endsAt": "0001-01-01T00:00:00Z",
                "fingerprint": "e2e_fingerprint_for_slack"
            }
        ]
    }
    
    # Step 3: Trigger the event
    send_alert_to_rabbitmq(test_payload)
    
    # Step 4: Verify the outcomes
    verify_results()
    
    print("\n🎉 E2E Test Passed Successfully! 🎉")
    sys.exit(0)