#!/usr/bin/env python3
import json
import requests
import argparse
import time
import uuid
import copy # Import copy for deep copying payloads
from datetime import datetime, timezone

# --- Constants ---
FIRING_PAYLOAD_FILE = 'one_fireing_alert.json'
DEFAULT_RESOLVE_DELAY = 120 # 2 minutes
DEFAULT_REFIRE_DELAY = 120   # 1 minute

# --- Helper Functions ---

def send_alert(url, alert_data, headers=None):
    """
    Send alert data to the webhook URL. (Unchanged)
    """
    if headers is None:
        headers = {
            'Content-Type': 'application/json',
        }
    try:
        print("\n--- Sending Data ---")
        print(json.dumps(alert_data, indent=2))
        print("--------------------")
        response = requests.post(url, json=alert_data, headers=headers)
        response.raise_for_status()
        print(f"Response Status: {response.status_code} {response.reason}")
        if response.status_code >= 200 and response.status_code < 300:
             print(">>> Alert sent successfully!")
             return True
        else:
             try:
                 print(f"Response Content: {response.json()}")
             except json.JSONDecodeError:
                 print(f"Response Content: {response.text}")
             return False
    except requests.exceptions.RequestException as e:
        print(f"Error sending alert: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print(f"Server Response: {e.response.status_code} {e.response.reason}")
             try:
                 print(f"Server Response Body: {e.response.json()}")
             except json.JSONDecodeError:
                 print(f"Server Response Body: {e.response.text}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False

def load_json_file(file_path):
    """
    Load JSON data from a file. (Unchanged)
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
        print(f"Error loading JSON from file {file_path}: {e}")
        return None

def get_current_utc_time_str():
    """ Returns current UTC time as ISO 8601 string with Z """
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

# --- Modified prepare_payload to accept and use a specific fingerprint ---
def prepare_payload(base_alert_data, target_status, fingerprint_to_use):
    """
    Prepares a payload based on the base data for a specific status ('firing' or 'resolved').
    Uses the provided fingerprint. Updates timestamps appropriately.

    Args:
        base_alert_data (dict): The original alert structure loaded from the file.
        target_status (str): Either 'firing' or 'resolved'.
        fingerprint_to_use (str): The fingerprint to set for this alert instance.

    Returns:
        dict: The prepared payload ready to be sent.
    """
    payload = copy.deepcopy(base_alert_data)
    current_time_str = get_current_utc_time_str()

    if 'alerts' in payload and isinstance(payload['alerts'], list) and len(payload['alerts']) > 0:
        alert = payload['alerts'][0] # Assuming one alert

        # --- Apply the provided fingerprint ---
        alert['fingerprint'] = fingerprint_to_use
        # Keep original labels
        original_labels = alert.get('labels', {})
        # --- Removed print statement for original fingerprint ---

        alert['status'] = target_status
        payload['status'] = target_status

        if target_status == 'firing':
            alert['startsAt'] = current_time_str
            alert['endsAt'] = "0001-01-01T00:00:00Z"
        elif target_status == 'resolved':
            alert['endsAt'] = current_time_str
            if 'startsAt' not in alert: # Ensure startsAt exists
                 alert['startsAt'] = "0001-01-01T00:00:00Z"
        else:
            print(f"Warning: Unknown target status '{target_status}'.")

    else:
        print("Warning: 'alerts' key invalid in base data. Cannot prepare payload.")
        return None

    return payload


def main():
    parser = argparse.ArgumentParser(
        description='Send a sequence of Firing -> Resolved -> Firing alerts using a base payload and a consistent random fingerprint per run.'
    )
    parser.add_argument('--url', default='http://localhost:8000/alerts/api/v1/webhook/',
                        help='Webhook URL')
    parser.add_argument('--resolve-delay', type=int, default=DEFAULT_RESOLVE_DELAY,
                        help=f'Delay in seconds before sending Resolved (default: {DEFAULT_RESOLVE_DELAY})')
    parser.add_argument('--refire-delay', type=int, default=DEFAULT_REFIRE_DELAY,
                        help=f'Delay in seconds before sending second Firing (default: {DEFAULT_REFIRE_DELAY})')
    parser.add_argument('--payload-file', default=FIRING_PAYLOAD_FILE,
                        help=f'Path to the base JSON payload file (default: {FIRING_PAYLOAD_FILE})')

    args = parser.parse_args()

    # --- Load Base Payload ---
    print(f"Loading base alert data from: {args.payload_file}")
    base_alert_data = load_json_file(args.payload_file)
    if not base_alert_data:
        print("Failed to load base alert data. Exiting.")
        return

    # --- Generate ONE new fingerprint for this entire script run ---
    run_fingerprint = uuid.uuid4().hex
    print(f"\n>>> Using Fingerprint for this run: {run_fingerprint} <<<")


    # --- Simulation Sequence ---
    print("\n>>> Starting Alert Simulation Sequence <<<")

    # 1. Send Initial Firing Alert (using run_fingerprint)
    print(f"\n[Step 1] Sending Initial 'firing' alert...")
    firing_payload_1 = prepare_payload(base_alert_data, 'firing', run_fingerprint)
    if firing_payload_1:
        send_alert(args.url, firing_payload_1)
    else:
        print("Failed to prepare initial firing payload. Aborting.")
        return

    # 2. Wait before Resolving
    print(f"\n[Step 2] Waiting for {args.resolve_delay} seconds before sending 'resolved'...")
    time.sleep(args.resolve_delay)

    # 3. Send Resolved Alert (using the SAME run_fingerprint)
    print(f"\n[Step 3] Sending 'resolved' alert...")
    resolved_payload = prepare_payload(base_alert_data, 'resolved', run_fingerprint)
    if resolved_payload:
        send_alert(args.url, resolved_payload)
    else:
        print("Failed to prepare resolved payload. Aborting.")
        return

    # 4. Wait before Re-firing
    print(f"\n[Step 4] Waiting for {args.refire_delay} seconds before sending 'firing' again...")
    time.sleep(args.refire_delay)

    # 5. Send Second Firing Alert (using the SAME run_fingerprint)
    print(f"\n[Step 5] Sending second 'firing' alert...")
    firing_payload_2 = prepare_payload(base_alert_data, 'firing', run_fingerprint)
    if firing_payload_2:
         send_alert(args.url, firing_payload_2)
    else:
        print("Failed to prepare second firing payload.")

    print("\n>>> Alert Simulation Sequence Finished <<<")


if __name__ == "__main__":
    main()