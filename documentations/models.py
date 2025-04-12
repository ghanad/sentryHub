# docs/models.py

from django.db import models
from django.utils import timezone
from tinymce.models import HTMLField


class AlertDocumentation(models.Model):
    title = models.CharField(max_length=255, help_text="Alert name (must match the alertname)")
    description = HTMLField(help_text="Description of the alert and problem")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_documentations'
    )
    
    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['title']
        verbose_name = "Alert Documentation"
        verbose_name_plural = "Alert Documentation"


class DocumentationAlertGroup(models.Model):
    """
    Association model to track which alert groups are linked to which documentation
    """
    documentation = models.ForeignKey(
        'AlertDocumentation',
        on_delete=models.CASCADE,
        related_name='alert_groups'
    )
    alert_group = models.ForeignKey(
        'alerts.AlertGroup',
        on_delete=models.CASCADE,
        related_name='documentation_links'
    )
    linked_at = models.DateTimeField(auto_now_add=True)
    linked_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='documentation_links'
    )
    
    class Meta:
        unique_together = ('documentation', 'alert_group')
        verbose_name = "Documentation-Alert Link"
        verbose_name_plural = "Documentation-Alert Links"