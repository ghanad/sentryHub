from django.db import models
from django.utils import timezone


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
    
    def __str__(self):
        return f"{self.name} ({self.fingerprint})"
    
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