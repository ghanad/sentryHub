# tests/e2e/run_test.py
import pika
import json
import time
import os
import sys
import requests

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
    # Setup Django to be able to query models
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sentryHub.settings')
    import django
    django.setup()
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
        slack_message = received_data["slack"][0]['text']
        assert "E2ESlackTest" in slack_message, f"Slack message content is incorrect: {slack_message}"
        print("✅ Slack verification successful: Message received by mock server.")

        # Check Jira (assuming this alert should also create a Jira ticket)
        # assert len(received_data["jira"]) > 0, "No ticket was created in Jira."
        # print("✅ Jira verification successful: Ticket created in mock server.")

    except (requests.RequestException, AssertionError) as e:
        print(f"❌ External integration verification failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    # Define a payload that will match your SlackIntegrationRule
    test_payload = {
        "alerts": [
            {
                "status": "firing",
                "labels": { "alertname": "E2ESlackTest", "severity": "critical", "service": "e2e-service" },
                "annotations": { "summary": "This is a full E2E test." },
                "startsAt": "2024-01-01T00:00:00Z",
                "endsAt": "0001-01-01T00:00:00Z",
                "fingerprint": "e2e_fingerprint_for_slack"
            }
        ]
    }
    
    send_alert_to_rabbitmq(test_payload)
    verify_results()
    
    print("\n🎉 E2E Test Passed Successfully! 🎉")
    sys.exit(0)