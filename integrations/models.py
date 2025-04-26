from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.models import User
import json
from alerts.models import AlertGroup


class JiraIntegrationRule(models.Model):
    """
    Defines a rule for creating/updating Jira issues based on alert properties.
    """
    name = models.CharField(max_length=100, unique=True)
    # description = models.TextField(blank=True) # Removed as requested
    is_active = models.BooleanField(default=True, db_index=True)
    # Match criteria defines WHICH alerts trigger this rule
    match_criteria = models.JSONField(
        default=dict,
        help_text='JSON object defining label match criteria. E.g., {"job": "node", "severity": "critical"}'
    )
    # Action defines WHAT happens in Jira
    jira_project_key = models.CharField(max_length=50, help_text="Target Jira project key (e.g., OPS)")
    jira_issue_type = models.CharField(max_length=50, help_text="Target Jira issue type (e.g., Bug, Task)")

    # Templates for Jira Issue content (use {{ variable }} syntax for alert labels/annotations)
    jira_title_template = models.TextField(
        blank=True,
        default="Alert: {{ alertname }} for {{ job }}",
        help_text="Template for the Jira issue title. Use {{ label_name }} or {{ annotation_name }}. Default: 'Alert: {{ alertname }} for {{ job }}'"
    )
    jira_description_template = models.TextField(
        blank=True,
        default="Firing alert details:\nLabels:\n{% for key, value in labels.items() %}  {{ key }}: {{ value }}\n{% endfor %}\nAnnotations:\n{% for key, value in annotations.items() %}  {{ key }}: {{ value }}\n{% endfor %}",
        help_text="Template for the Jira issue description. Uses Django template syntax. Available context: labels (dict), annotations (dict), alertname, status, etc. See documentation for full context."
    )
    jira_update_comment_template = models.TextField(
        blank=True,
        default="Alert status changed to {{ status }}. \n{% if status == 'firing' %}Labels:\n{% for key, value in labels.items() %}  {{ key }}: {{ value }}\n{% endfor %}{% endif %}",
        help_text="Template for the comment added when an existing Jira issue is updated (e.g., alert resolved or re-fired). Uses Django template syntax."
    )

    # Optional: Define priority if multiple rules might match
    priority = models.IntegerField(default=0, help_text="Higher priority rules are evaluated first.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority', 'name'] # Process higher priority first
        verbose_name = "Jira Integration Rule"
        verbose_name_plural = "Jira Integration Rules"

    def clean(self):
        """Validate that match_criteria is a valid JSON dictionary."""
        super().clean()
        if not isinstance(self.match_criteria, dict):
            raise ValidationError({'match_criteria': 'Must be a valid JSON object (dictionary).'})

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.name} ({status}, Prio: {self.priority})"
