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
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    # Match criteria defines WHICH alerts trigger this rule
    match_criteria = models.JSONField(
        default=dict,
        help_text='JSON object defining label match criteria. E.g., {"job": "node", "severity": "critical"}'
    )
    # Action defines WHAT happens in Jira
    jira_project_key = models.CharField(max_length=50, help_text="Target Jira project key (e.g., OPS)")
    jira_issue_type = models.CharField(max_length=50, help_text="Target Jira issue type (e.g., Bug, Task)")
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
