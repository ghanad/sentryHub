from dateutil.parser import parse as parse_datetime
from typing import List, Dict, Any

def parse_alertmanager_payload(payload: dict) -> List[Dict[str, Any]]:
    """
    Parse Alertmanager webhook payload into standardized alert data.
    
    Args:
        payload: Raw Alertmanager webhook payload
        
    Returns:
        List of standardized alert dictionaries with keys:
        - fingerprint: str
        - status: str ('firing' or 'resolved')
        - labels: dict
        - annotations: dict
        - starts_at: datetime
        - ends_at: datetime or None
        - generator_url: str
    """
    alerts = []
    
    # Handle both v1 and v2 Alertmanager payload formats
    if 'alerts' in payload:
        alert_list = payload['alerts']
    else:
        alert_list = [payload]  # Handle single alert format
    
    for alert_data in alert_list:
        fingerprint = alert_data.get('fingerprint')
        status = alert_data.get('status')
        labels = alert_data.get('labels', {})
        annotations = alert_data.get('annotations', {})
        
        # Parse timestamps
        starts_at = parse_datetime(alert_data.get('startsAt'))
        ends_at = parse_datetime(alert_data.get('endsAt')) if alert_data.get('endsAt') != '0001-01-01T00:00:00Z' else None
        
        generator_url = alert_data.get('generatorURL')
        
        # Get the 'source' label
        source_identifier = alert_data.get('labels', {}).get('source')

        alerts.append({
            'fingerprint': fingerprint,
            'status': status,
            'labels': labels,
            'annotations': annotations,
            'starts_at': starts_at,
            'ends_at': ends_at,
            'generator_url': generator_url,
            'source': source_identifier  # Add the new source field
        })
    
    return alerts