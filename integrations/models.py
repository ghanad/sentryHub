from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.models import User
import json
from alerts.models import AlertGroup

class JiraRuleMatcher(models.Model):
    """
    A single matcher criterion for a JiraIntegrationRule, based on alert labels.
    Uses JSONField for flexibility. Example: {"severity": "critical", "namespace": "prod-.*"}
    Values can be exact strings or regex patterns.
    """
    name = models.CharField(max_length=100, help_text="Identifier for this matcher set")
    # Store match criteria as JSON: {"label_name": "value_or_regex", ...}
    match_criteria = models.JSONField(
        default=dict,
        help_text='JSON object where keys are label names and values are exact strings or regex patterns to match. Example: {"severity": "critical", "cluster": "prod-us-east-.*"}'
    )
    is_regex = models.BooleanField(default=False, help_text="Set to True if any values in match_criteria are regex patterns.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        """ Validate that match_criteria is a valid JSON dictionary. """
        super().clean()
        if not isinstance(self.match_criteria, dict):
            raise ValidationError({'match_criteria': 'Must be a valid JSON object (dictionary).'})
        # Optional: Further validation for keys/values if needed

    def __str__(self):
        # Provide a more informative representation
        try:
            criteria_str = json.dumps(self.match_criteria, ensure_ascii=False, indent=None)
            return f"{self.name}: {criteria_str} (Regex: {self.is_regex})"
        except TypeError:
             return f"{self.name}: Invalid JSON (Regex: {self.is_regex})"


class JiraIntegrationRule(models.Model):
    """
    Defines a rule for creating/updating Jira issues based on alert properties.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    # Matchers define WHICH alerts trigger this rule. A rule matches if ALL its matchers are satisfied.
    matchers = models.ManyToManyField(
        'JiraRuleMatcher',
        related_name='rules',
         help_text="Select one or more matchers. The rule applies if ALL selected matchers match the alert's labels."
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

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.name} ({status}, Prio: {self.priority})"
