from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
import json # Added for SilenceRule __str__ potentially


class AlertGroup(models.Model):
    fingerprint = models.CharField(max_length=255, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    labels = models.JSONField()
    severity = models.CharField(
        max_length=20,
        choices=[
            ('critical', 'Critical'),
            ('warning', 'Warning'),
            ('info', 'Info'),
        ],
        default='warning'
    )
    
    instance = models.CharField(max_length=255, blank=True, null=True, db_index=True,
        help_text="Instance address (IP or hostname) extracted from labels")
    
    source = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        help_text="Identifier for the source Alertmanager instance"
    )

    first_occurrence = models.DateTimeField(auto_now_add=True)
    last_occurrence = models.DateTimeField(auto_now=True)
    current_status = models.CharField(
        max_length=20,
        choices=[
            ('firing', 'Firing'),
            ('resolved', 'Resolved'),
        ],
        default='firing'
    )
    total_firing_count = models.PositiveIntegerField(default=1)
    acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_alerts'
    )
    acknowledgement_time = models.DateTimeField(null=True, blank=True)
    documentation = models.ForeignKey(
        'docs.AlertDocumentation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='directly_linked_alerts'
    )
    is_silenced = models.BooleanField(default=False, help_text="Is this alert group currently silenced by an internal rule?")
    silenced_until = models.DateTimeField(null=True, blank=True, help_text="If silenced, when does the current silence rule end?")
    jira_issue_key = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Jira Issue Key",
        help_text="The key of the Jira issue associated with this alert group (e.g., PROJECT-123)."
    )

    def __str__(self):
        base_str = f"{self.name} ({self.instance or self.fingerprint})"
        if self.jira_issue_key:
            base_str += f" [Jira: {self.jira_issue_key}]"
        return base_str
    
    class Meta:
        ordering = ['-last_occurrence']


class AlertInstance(models.Model):
    alert_group = models.ForeignKey(
        'AlertGroup',
        on_delete=models.CASCADE,
        related_name='instances'
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('firing', 'Firing'),
            ('resolved', 'Resolved'),
        ]
    )
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    annotations = models.JSONField()
    generator_url = models.URLField(max_length=500, null=True, blank=True)
    resolution_type = models.CharField(
        max_length=20,
        choices=[
            ('normal', 'Normal Resolution'),
            ('inferred', 'Inferred Resolution'),
            ('manual', 'Manual Resolution'),
        ],
        null=True,
        blank=True
    )
    
    def __str__(self):
        return f"{self.alert_group.name} - {self.status} at {self.started_at}"
    
    class Meta:
        ordering = ['-started_at']


class AlertComment(models.Model):
    alert_group = models.ForeignKey(
        'AlertGroup',
        on_delete=models.CASCADE,
        related_name='comments'
    )
    user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='alert_comments'
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Comment by {self.user.username} on {self.alert_group.name}"
    
    class Meta:
        ordering = ['-created_at']


class AlertAcknowledgementHistory(models.Model):
    """
    Track the history of alert acknowledgements.
    This helps in determining who acknowledged which instance of an alert.
    """
    alert_group = models.ForeignKey(
        'AlertGroup',
        on_delete=models.CASCADE,
        related_name='acknowledgement_history'
    )
    alert_instance = models.ForeignKey(
        'AlertInstance',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledgements'
    )
    acknowledged_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='alert_acknowledgements'
    )
    acknowledged_at = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(null=True, blank=True)
    
    def __str__(self):
        instance_info = f" (Instance ID: {self.alert_instance.id})" if self.alert_instance else ""
        return f"Acknowledgement by {self.acknowledged_by.username} on {self.alert_group.name}{instance_info}"
    
    class Meta:
        ordering = ['-acknowledged_at']


class SilenceRule(models.Model):
    matchers = models.JSONField(
        help_text='Labels to match exactly. E.g., {"job": "node_exporter", "instance": "server1"}'
    )
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_silence_rules')
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_active(self):
        now = timezone.now()
        return self.starts_at <= now < self.ends_at

    def __str__(self):
        try:
            match_str = ", ".join([f'{k}="{v}"' for k, v in self.matchers.items()])
        except AttributeError: # Handle cases where matchers might not be a dict (e.g., null or invalid JSON)
            match_str = "Invalid Matchers"
        user_str = self.created_by.username if self.created_by else 'System'
        return f"Silence rule for {match_str} (by {user_str})"

    class Meta:
        ordering = ['-starts_at']
        verbose_name = "Silence Rule"
        verbose_name_plural = "Silence Rules"


