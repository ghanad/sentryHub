#!/usr/bin/env python3
import json
import requests
import argparse
import time
from datetime import datetime

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
        response = requests.post(url, json=alert_data, headers=headers)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        print(f"Error sending alert: {e}")
        return None

def load_alerts_from_file(file_path):
    """
    Load alerts from a JSON file
    
    Args:
        file_path (str): Path to the JSON file
    
    Returns:
        dict: Loaded alert data
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error loading alerts from file: {e}")
        return None

def update_alert_timestamps(alert_data, shift_minutes=0):
    """
    Update alert timestamps to current time
    
    Args:
        alert_data (dict): Alert data
        shift_minutes (int): Minutes to shift between alerts
    
    Returns:
        dict: Updated alert data
    """
    current_time = datetime.utcnow()
    updated_data = alert_data.copy()
    
    # Handle different alert data structures
    if 'alerts' in updated_data:
        for i, alert in enumerate(updated_data['alerts']):
            # Calculate offset timestamp for each alert
            offset_minutes = i * shift_minutes
            alert_time = current_time.replace(microsecond=0)
            
            # Update startsAt
            if 'startsAt' in alert:
                alert['startsAt'] = (alert_time.isoformat() + 'Z')
            
            # Update endsAt for resolved alerts
            if 'endsAt' in alert and alert.get('status') == 'resolved':
                if alert['endsAt'] != '0001-01-01T00:00:00Z':
                    # Calculate an appropriate end time (typically a few minutes after start)
                    alert['endsAt'] = (alert_time.isoformat() + 'Z')
    
    return updated_data

def main():
    parser = argparse.ArgumentParser(description='Send alerts to SentryHub webhook')
    parser.add_argument('file', help='JSON file containing alert data')
    parser.add_argument('--url', default='http://localhost:8000/api/v1/webhook/', 
                      help='Webhook URL (default: http://localhost:8000/api/v1/webhook/)')
    parser.add_argument('--update-time', action='store_true', 
                      help='Update alert timestamps to current time')
    parser.add_argument('--stagger', action='store_true',
                      help='Send alerts one by one with delay')
    parser.add_argument('--delay', type=int, default=5,
                      help='Delay in seconds between alerts when using --stagger (default: 5)')
    parser.add_argument('--shift', type=int, default=5,
                      help='Minutes to shift between alert timestamps when using --update-time (default: 5)')
    
    args = parser.parse_args()
    
    # Load alerts from file
    alert_data = load_alerts_from_file(args.file)
    if not alert_data:
        return
    
    # Update timestamps if requested
    if args.update_time:
        alert_data = update_alert_timestamps(alert_data, args.shift)
    
    # Send all alerts at once
    if not args.stagger:
        print(f"Sending alerts to {args.url}")
        response = send_alert(args.url, alert_data)
        if response:
            print(f"Response: {response.status_code} {response.reason}")
            if response.status_code == 200:
                print("Alerts sent successfully!")
            else:
                print(f"Response content: {response.text}")
    else:
        # Send alerts one by one with delay
        if 'alerts' in alert_data:
            base_data = {key: value for key, value in alert_data.items() if key != 'alerts'}
            
            for i, alert in enumerate(alert_data['alerts']):
                print(f"Sending alert {i+1}/{len(alert_data['alerts'])}")
                
                # Create a new alert data with a single alert
                single_alert_data = base_data.copy()
                single_alert_data['alerts'] = [alert]
                
                # Send the alert
                response = send_alert(args.url, single_alert_data)
                if response:
                    print(f"Response: {response.status_code} {response.reason}")
                
                # Wait before sending the next alert
                if i < len(alert_data['alerts']) - 1:
                    print(f"Waiting {args.delay} seconds before sending next alert...")
                    time.sleep(args.delay)
        else:
            print("Warning: No 'alerts' array found in the data, sending as is")
            response = send_alert(args.url, alert_data)
            if response:
                print(f"Response: {response.status_code} {response.reason}")

if __name__ == "__main__":
    main()