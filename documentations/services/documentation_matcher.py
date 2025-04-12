from django.utils import timezone
import logging

from docs.models import AlertDocumentation, DocumentationAlertGroup

logger = logging.getLogger(__name__)

def match_documentation_to_alert(alert_group, user=None):
    """
    Attempt to automatically match documentation to an alert group based on exact title match.
    
    Args:
        alert_group: AlertGroup instance
        user: User who triggered the match (optional)
        
    Returns:
        matched_doc: AlertDocumentation instance if match found, None otherwise
    """
    alert_name = alert_group.name
    
    logger.info(f"Attempting to match documentation for alert: {alert_name}")
    
    try:
        # Look for documentation with exact title match
        documentation = AlertDocumentation.objects.filter(title=alert_name).first()
        
        if not documentation:
            logger.info(f"No documentation found with title matching: {alert_name}")
            return None
            
        logger.info(f"Found matching documentation: {documentation.title} (ID: {documentation.id})")
        
        # Create the link between documentation and alert
        link, created = DocumentationAlertGroup.objects.get_or_create(
            documentation=documentation,
            alert_group=alert_group,
            defaults={
                'linked_at': timezone.now(),
                'linked_by': user
            }
        )
        
        if created:
            logger.info(f"Successfully linked documentation {documentation.id} to alert {alert_group.id}")
        else:
            logger.info(f"Documentation {documentation.id} was already linked to alert {alert_group.id}")
        
        return documentation
        
    except Exception as e:
        logger.error(f"Error in match_documentation_to_alert: {str(e)}")
        return None


def get_documentation_for_alert(alert_group):
    """
    Get all documentation linked to an alert group.
    
    Args:
        alert_group: AlertGroup instance
        
    Returns:
        queryset: QuerySet of AlertDocumentation instances
    """
    return AlertDocumentation.objects.filter(
        alert_groups__alert_group=alert_group
    )