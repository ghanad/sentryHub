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
    assignee = models.CharField(
        max_length=100,
        blank=True,
        help_text="Jira username to assign the issue to (leave blank for no assignment)"
    )

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

        # Validate watchers format if needed (e.g., comma-separated usernames)
        # For now, we assume the task will handle parsing/validation

    watchers = models.TextField(
        blank=True,
        help_text="Comma-separated list of Jira usernames to add as watchers (e.g., user1,user2,user3)"
    )

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.name} ({status}, Prio: {self.priority})"

    def get_assignee(self):
        """Get the assignee username or None if not set"""
        return self.assignee if self.assignee else None


class SlackIntegrationRule(models.Model):
    """Defines rules for sending Slack notifications for alerts."""

    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True, db_index=True)
    priority = models.IntegerField(
        default=0, help_text="Higher priority rules are evaluated first."
    )
    match_criteria = models.JSONField(
        default=dict,
        help_text=
        'JSON object to match AlertGroup attributes. Use "labels__<key>" for label matching and regular field names or lookups (e.g., "source", "jira_issue_key__isnull") for AlertGroup properties.'
    )
    slack_channel = models.CharField(
        max_length=100,
        help_text="Destination Slack channel (e.g., #critical-alerts)"
    )
    message_template = models.TextField(
        blank=True,
        help_text="Template for Slack message. Uses Django template syntax."
    )
    resolved_message_template = models.TextField(
        blank=True,
        help_text="Template used when an alert is resolved. Uses Django template syntax."
    )

    class Meta:
        ordering = ['-priority', 'name']
        verbose_name = "Slack Integration Rule"
        verbose_name_plural = "Slack Integration Rules"

    def clean(self):
        """Validate that match_criteria is a JSON object."""
        super().clean()
        if not isinstance(self.match_criteria, dict):
            raise ValidationError({'match_criteria': 'Must be a valid JSON object (dictionary).'})

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.name} ({status}, Prio: {self.priority})"
