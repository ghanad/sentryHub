#!/usr/bin/env python
"""
Script to generate fake alert data for testing the SentryHub application.
Run this script after setting up the Django project to populate the database
with sample alerts.
"""

import os
import sys
import random
import json
import datetime
import requests
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sentryHub.settings')
import django
django.setup()

from django.utils import timezone
from django.contrib.auth.models import User
from alerts.models import AlertGroup, AlertInstance, AlertComment

# Configuration
NUM_ALERT_GROUPS = 20
NUM_INSTANCES_PER_GROUP = 15
NUM_COMMENTS = 30
SERVER_URL = "http://localhost:8000"

# Sample data
ALERT_NAMES = [
    "HighCPULoad", "MemoryUsageHigh", "DiskSpaceLow", "HighNetworkTraffic",
    "ServiceDown", "DatabaseConnectionFailed", "APIResponseSlow", "ErrorRateHigh",
    "JobFailed", "ReplicationLag", "CertificateExpiringSoon", "HighLatency",
    "NodeDown", "PrometheusTargetMissing", "CacheMissRateHigh", "QueueSizeIncreasing"
]

INSTANCE_NAMES = [
    "server01:9100", "server02:9100", "prod-db-01:9187", "prod-db-02:9187",
    "web-01:9100", "web-02:9100", "api-01:9100", "api-02:9100",
    "cache-01:9121", "cache-02:9121", "queue-01:9100", "queue-02:9100"
]

SEVERITY_LEVELS = ["critical", "warning", "info"]
SEVERITY_WEIGHTS = [0.2, 0.5, 0.3]  # Probability weights for each severity

USERS = []  # Will be populated with existing users

def create_users():
    """Create some test users if they don't exist."""
    usernames = ["operator1", "operator2", "admin1"]
    
    for username in usernames:
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": f"{username}@example.com", "is_staff": True}
        )
        if created:
            user.set_password("password123")
            user.save()
            print(f"Created user: {username}")
        
        USERS.append(user)
    
    return USERS

def generate_alert_data(alert_name, instance, severity, status="firing"):
    """Generate a complete alert data structure as expected by the webhook."""
    now = timezone.now()
    
    # For resolved alerts, set end time
    if status == "resolved":
        ends_at = now.isoformat()
    else:
        ends_at = "0001-01-01T00:00:00Z"
    
    # Generate random fingerprint for uniqueness
    fingerprint = f"{alert_name}-{instance}-{random.randint(100000, 999999)}"
    
    annotations = {
        "summary": f"{alert_name} on {instance}",
    }
    
    # Add different descriptions based on alert type
    if "CPU" in alert_name:
        annotations["description"] = f"CPU usage on {instance} is above 80%"
    elif "Memory" in alert_name:
        annotations["description"] = f"Memory usage on {instance} is above 90%"
    elif "Disk" in alert_name:
        annotations["description"] = f"Disk space on {instance} is below 10%"
    elif "Network" in alert_name:
        annotations["description"] = f"Network traffic on {instance} is abnormally high"
    elif "Service" in alert_name or "Down" in alert_name:
        annotations["description"] = f"Service on {instance} is not responding"
    elif "Database" in alert_name:
        annotations["description"] = f"Database connection from {instance} failed"
    else:
        annotations["description"] = f"{alert_name} issue detected on {instance}"
    
    return {
        "status": status,
        "labels": {
            "alertname": alert_name,
            "instance": instance,
            "job": instance.split(':')[0],
            "severity": severity
        },
        "annotations": annotations,
        "startsAt": (now - datetime.timedelta(minutes=random.randint(1, 60))).isoformat(),
        "endsAt": ends_at,
        "generatorURL": f"http://prometheus.example.com/graph?g0.expr={alert_name}",
        "fingerprint": fingerprint
    }

def generate_webhook_payload(alerts):
    """Creates a complete webhook payload with the given alerts."""
    return {
        "receiver": "webhook",
        "status": "firing" if any(alert["status"] == "firing" for alert in alerts) else "resolved",
        "alerts": alerts,
        "groupLabels": {},
        "commonLabels": {},
        "commonAnnotations": {},
        "externalURL": "http://alertmanager.example.com",
        "version": "4",
        "groupKey": "{}:{}"
    }

def send_webhook(payload):
    """Send the webhook payload to the API endpoint."""
    try:
        response = requests.post(
            f"{SERVER_URL}/api/v1/webhook/",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        return response.status_code == 200, response.text
    except requests.RequestException as e:
        return False, str(e)

def create_alerts_through_model():
    """Create alerts directly using Django models (alternative to webhook)."""
    print("\nCreating alerts using Django models...")
    
    for i in range(1, NUM_ALERT_GROUPS + 1):
        alert_name = random.choice(ALERT_NAMES)
        instance = random.choice(INSTANCE_NAMES)
        severity = random.choices(SEVERITY_LEVELS, weights=SEVERITY_WEIGHTS)[0]
        fingerprint = f"model-{alert_name}-{instance}-{i}"
        
        # Decide if alert is currently firing or resolved
        current_status = random.choice(["firing", "resolved"])
        
        # Create the AlertGroup
        alert_group = AlertGroup.objects.create(
            fingerprint=fingerprint,
            name=alert_name,
            labels={
                "alertname": alert_name,
                "instance": instance,
                "job": instance.split(':')[0],
                "severity": severity
            },
            severity=severity,
            current_status=current_status,
            total_firing_count=random.randint(1, 10)
        )
        
        # Create a random number of instances for this group
        instances_count = random.randint(1, NUM_INSTANCES_PER_GROUP)
        
        # Start time for the first instance
        start_time = timezone.now() - relativedelta(days=random.randint(1, 30))
        
        for j in range(instances_count):
            # Each instance starts after the previous one
            instance_start = start_time + relativedelta(hours=random.randint(1, 24))
            
            # For all but the last instance, set an end time
            instance_end = None
            if j < instances_count - 1 or current_status == "resolved":
                instance_end = instance_start + relativedelta(minutes=random.randint(10, 240))
            
            # Alternate between firing and resolved for historical instances
            instance_status = "firing" if j % 2 == 0 else "resolved"
            
            # For the last instance, use the current status
            if j == instances_count - 1:
                instance_status = current_status
            
            AlertInstance.objects.create(
                alert_group=alert_group,
                status=instance_status,
                started_at=instance_start,
                ended_at=instance_end,
                annotations={
                    "summary": f"{alert_name} on {instance}",
                    "description": f"Instance {j+1} of {alert_name} on {instance}"
                },
                generator_url=f"http://prometheus.example.com/graph?g0.expr={alert_name}"
            )
            
            # Update the start time for the next instance
            start_time = instance_start
            
            if j == instances_count - 1 and current_status == "firing":
                # If the last instance is firing, update the group's last_occurrence
                alert_group.last_occurrence = instance_start
                alert_group.save()
        
        print(f"Created AlertGroup: {alert_group.name} with {instances_count} instances")

def create_comments():
    """Create some random comments on alerts."""
    print("\nCreating comments...")
    
    alert_groups = list(AlertGroup.objects.all())
    if not alert_groups:
        print("No alert groups found to add comments to.")
        return
    
    for i in range(NUM_COMMENTS):
        alert_group = random.choice(alert_groups)
        user = random.choice(USERS)
        
        comment_types = [
            f"Investigating the {alert_group.name} issue on {random.choice(list(alert_group.labels.values()))}",
            f"This {alert_group.name} alert seems to be a false positive.",
            f"Restarted the service to resolve {alert_group.name} alert.",
            f"Applied patch to fix the {alert_group.name} issue.",
            f"The {alert_group.name} alert is related to the recent deployment.",
            f"Monitoring the situation with {alert_group.name}."
        ]
        
        comment = AlertComment.objects.create(
            alert_group=alert_group,
            user=user,
            content=random.choice(comment_types),
            created_at=timezone.now() - relativedelta(minutes=random.randint(5, 1440))
        )
        
        print(f"Created comment by {user.username} on {alert_group.name}")

def acknowledge_some_alerts():
    """Acknowledge some of the alerts."""
    print("\nAcknowledging some alerts...")
    
    # Get all firing alerts
    firing_alerts = AlertGroup.objects.filter(current_status='firing', acknowledged=False)
    
    # Acknowledge about half of them
    alerts_to_acknowledge = list(firing_alerts)[:len(firing_alerts)//2]
    
    for alert in alerts_to_acknowledge:
        user = random.choice(USERS)
        alert.acknowledged = True
        alert.acknowledged_by = user
        alert.acknowledgement_time = timezone.now() - relativedelta(minutes=random.randint(5, 60))
        alert.save()
        
        # Add an acknowledgment comment
        AlertComment.objects.create(
            alert_group=alert,
            user=user,
            content=f"Alert acknowledged. Working on resolution.",
            created_at=alert.acknowledgement_time
        )
        
        print(f"Acknowledged alert: {alert.name} by {user.username}")

def main():
    print("Starting to generate fake alert data...")
    
    # Create test users
    users = create_users()
    if not users:
        print("Failed to create users. Exiting.")
        return
    
    # Method 1: Send alerts through the webhook API
    print("\nSending alerts through webhook API...")
    
    for i in range(1, NUM_ALERT_GROUPS // 2 + 1):
        # For each alert group, create a random number of alerts
        num_alerts = random.randint(1, 3)
        alerts = []
        
        for j in range(num_alerts):
            alert_name = random.choice(ALERT_NAMES)
            instance = random.choice(INSTANCE_NAMES)
            severity = random.choices(SEVERITY_LEVELS, weights=SEVERITY_WEIGHTS)[0]
            status = random.choice(["firing", "resolved"])
            
            alert = generate_alert_data(alert_name, instance, severity, status)
            alerts.append(alert)
        
        payload = generate_webhook_payload(alerts)
        
        success, result = send_webhook(payload)
        if success:
            print(f"Successfully sent webhook with {num_alerts} alerts")
        else:
            print(f"Failed to send webhook: {result}")
            print("Falling back to creating alerts through Django models...")
            break
    
    # Method 2: Create alerts directly through Django models
    create_alerts_through_model()
    
    # Add comments to some alerts
    create_comments()
    
    # Acknowledge some alerts
    acknowledge_some_alerts()
    
    print("\nFake data generation complete!")

if __name__ == "__main__":
    main()