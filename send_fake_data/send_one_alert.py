#!/usr/bin/env python3
import json
import requests
import argparse
import time
import uuid  # Import uuid for generating random fingerprint
from datetime import datetime, timezone # Import timezone


def send_alert(url, alert_data, headers=None):
    """
    Send alert data to the webhook URL

    Args:
        url (str): Webhook URL
        alert_data (dict): Alert data to send
        headers (dict): Optional HTTP headers

    Returns:
        requests.Response: Response from the server
    """
    if headers is None:
        headers = {
            'Content-Type': 'application/json',
        }

    try:
        # Print the data being sent for debugging
        print("--- Sending Data ---")
        print(json.dumps(alert_data, indent=2))
        print("--------------------")

        response = requests.post(url, json=alert_data, headers=headers)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        print(f"Error sending alert: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print(f"Server Response: {e.response.status_code} {e.response.reason}")
             try:
                 print(f"Server Response Body: {e.response.json()}")
             except json.JSONDecodeError:
                 print(f"Server Response Body: {e.response.text}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


def load_alerts_from_file(file_path):
    """
    Load alerts from a JSON file

    Args:
        file_path (str): Path to the JSON file

    Returns:
        dict: Loaded alert data or None if error
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from file {file_path}: {e}")
        return None
    except Exception as e:
        print(f"Error loading alerts from file {file_path}: {e}")
        return None

def modify_alert_data(alert_data):
    """
    Update alert timestamps to current UTC time and randomize fingerprint.

    Args:
        alert_data (dict): Alert data

    Returns:
        dict: Updated alert data
    """
    # Get current time in UTC
    # Using timezone.utc ensures it's timezone-aware UTC
    current_time_utc = datetime.now(timezone.utc)
    # Format as ISO 8601 with 'Z' for UTC, removing microseconds
    current_time_str = current_time_utc.strftime('%Y-%m-%dT%H:%M:%SZ')

    updated_data = alert_data.copy() # Work on a copy

    if 'alerts' in updated_data and isinstance(updated_data['alerts'], list):
        for alert in updated_data['alerts']:
            # Update startsAt to current UTC time
            if 'startsAt' in alert:
                print(f"Updating startsAt from {alert.get('startsAt')} to {current_time_str}")
                alert['startsAt'] = current_time_str

            # Update fingerprint to a random UUID hex string
            if 'fingerprint' in alert:
                new_fingerprint = uuid.uuid4().hex
                print(f"Updating fingerprint from {alert.get('fingerprint')} to {new_fingerprint}")
                alert['fingerprint'] = new_fingerprint

            # Ensure endsAt is correct for firing alerts
            if alert.get('status') == 'firing' and 'endsAt' in alert:
                 # Alertmanager often uses this for firing alerts
                 alert['endsAt'] = "0001-01-01T00:00:00Z"

    else:
        print("Warning: 'alerts' key not found or is not a list in the data. No modifications applied.")

    return updated_data

def main():
    parser = argparse.ArgumentParser(description='Send a modified alert from one_firing_alert.json to a webhook.')
    # Removed the 'file' argument, hardcoding the filename
    parser.add_argument('--url', default='http://localhost:8000/alerts/api/v1/webhook/',
                      help='Webhook URL (default: http://localhost:8000/alerts/api/v1/webhook/)')
    # Removed --update-time, --stagger, --delay, --shift arguments

    args = parser.parse_args()

    # Hardcoded file path
    file_path = 'one_fireing_alert.json'
    print(f"Loading alert data from: {file_path}")

    # Load alerts from the specific file
    alert_data = load_alerts_from_file(file_path)
    if not alert_data:
        print("Failed to load alert data. Exiting.")
        return # Exit if loading failed

    # Modify the alert data (update time, randomize fingerprint)
    print("Modifying alert data (timestamp, fingerprint)...")
    modified_alert_data = modify_alert_data(alert_data)

    # Send the modified alert
    print(f"Sending modified alert to {args.url}")
    response = send_alert(args.url, modified_alert_data)

    if response:
        print(f"Response Status: {response.status_code} {response.reason}")
        if response.status_code >= 200 and response.status_code < 300:
            print("Alert sent successfully!")
        else:
            # Try to print response body for non-successful status codes
            try:
                print(f"Response Content: {response.json()}")
            except json.JSONDecodeError:
                print(f"Response Content: {response.text}")
    else:
        print("Failed to send alert.")


if __name__ == "__main__":
    main()
