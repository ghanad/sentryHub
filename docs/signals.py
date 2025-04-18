from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import AlertDocumentation
from alerts.models import AlertGroup
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=AlertDocumentation)
def handle_documentation_save(sender, instance: AlertDocumentation, created, **kwargs):
    """
    When AlertDocumentation is saved (created or updated), find existing AlertGroups
    with a matching name and create the link.
    """
    # Import the link model here to avoid potential circular imports at module level
    from .models import DocumentationAlertGroup
    from django.utils import timezone

    alert_name_to_match = instance.title
    logger.info(f"post_save signal received for AlertDocumentation '{alert_name_to_match}' (ID: {instance.id}). Checking for matching AlertGroups.")

    # Find existing AlertGroups with the same name as the documentation title
    matching_alert_groups = AlertGroup.objects.filter(name=alert_name_to_match)

    linked_count = 0
    already_linked_count = 0

    for alert_group in matching_alert_groups:
        # Use get_or_create to avoid duplicate links and race conditions
        link, link_created = DocumentationAlertGroup.objects.get_or_create(
            documentation=instance,
            alert_group=alert_group,
            # Set defaults for creation, like the user who created/updated the doc
            # Note: 'created_by' might not be the best user here if someone else updates the doc.
            # Consider passing the user from the view if possible, or leave it null.
            defaults={'linked_by': instance.created_by}
        )

        if link_created:
            linked_count += 1
            logger.info(f"Created link between Doc ID {instance.id} and AlertGroup ID {alert_group.id} ('{alert_group.name}')")
        else:
            already_linked_count += 1
            # Optionally update linked_at or linked_by if the doc was updated
            # link.linked_at = timezone.now()
            # link.save(update_fields=['linked_at'])

    if linked_count > 0:
        logger.info(f"Successfully linked documentation '{alert_name_to_match}' to {linked_count} new AlertGroups.")
    if already_linked_count > 0:
         logger.debug(f"Documentation '{alert_name_to_match}' was already linked to {already_linked_count} AlertGroups.")
    if linked_count == 0 and already_linked_count == 0:
        logger.info(f"No existing AlertGroups found matching the name '{alert_name_to_match}' for linking.")

    # Note: This doesn't handle unlinking if the documentation title changes.
    # That would require knowing the previous title or a more complex cleanup process.