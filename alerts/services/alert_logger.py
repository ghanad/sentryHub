import os
import json
from datetime import datetime
from django.conf import settings

def save_alert_to_file(alert_data):
    """
    Save alert data to a JSON file in the Logs directory.
    The filename will be based on the current date and time.
    
    Args:
        alert_data (dict): The alert data to save
    """
    # Create Logs directory if it doesn't exist
    logs_dir = os.path.join(settings.BASE_DIR, 'Logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Generate filename based on current date and time
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'alert_{timestamp}.json'
    filepath = os.path.join(logs_dir, filename)
    
    # Save alert data to file
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(alert_data, f, indent=2, ensure_ascii=False) 