import json
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import (
    AlertGroup, AlertInstance, AlertComment,
    AlertAcknowledgementHistory, SilenceRule
)


@admin.register(AlertGroup)
class AlertGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'instance', 'fingerprint', 'severity',
                    'current_status', 'total_firing_count',
                    'first_occurrence', 'last_occurrence', 'acknowledged',
                    'jira_issue_key_link')
    list_filter = ('severity', 'current_status', 'acknowledged')
    search_fields = ('name', 'fingerprint', 'instance', 'jira_issue_key')
    date_hierarchy = 'first_occurrence'
    readonly_fields = ('jira_issue_key_link',)

    def jira_issue_key_link(self, obj):
        """Displays Jira issue key as link if configured."""
        if obj.jira_issue_key:
            from django.conf import settings
            jira_url = settings.JIRA_CONFIG.get('server_url', '').rstrip('/')
            if jira_url:
                return mark_safe(f'<a href="{jira_url}/browse/{obj.jira_issue_key}" target="_blank">{obj.jira_issue_key}</a>')
        return obj.jira_issue_key or '-'
    jira_issue_key_link.short_description = 'Jira Issue'


@admin.register(AlertInstance)
class AlertInstanceAdmin(admin.ModelAdmin):
    list_display = ('alert_group', 'status', 'started_at', 'ended_at')
    list_filter = ('status',)
    search_fields = ('alert_group__name', 'alert_group__fingerprint')
    date_hierarchy = 'started_at'


@admin.register(AlertComment)
class AlertCommentAdmin(admin.ModelAdmin):
    list_display = ('alert_group', 'user', 'content', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('alert_group__name', 'user__username', 'content')
    date_hierarchy = 'created_at'


@admin.register(AlertAcknowledgementHistory)
class AlertAcknowledgementHistoryAdmin(admin.ModelAdmin):
    list_display = ('alert_group', 'alert_instance', 'acknowledged_by', 'acknowledged_at')
    list_filter = ('acknowledged_at',)
    search_fields = ('alert_group__name', 'acknowledged_by__username')
    date_hierarchy = 'acknowledged_at'


@admin.register(SilenceRule)
class SilenceRuleAdmin(admin.ModelAdmin):
    list_display = ('id', 'display_matchers_short', 'starts_at', 'ends_at', 'is_active_display', 'created_by', 'created_at', 'comment_short')
    list_filter = ('starts_at', 'ends_at', 'created_by')
    search_fields = ('comment', 'created_by__username', 'matchers__icontains') # Basic JSON search
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('matchers', 'comment')
        }),
        ('Duration', {
            'fields': ('starts_at', 'ends_at')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',) # Keep metadata collapsed by default
        }),
    )

    def display_matchers_short(self, obj):
        """Displays a shortened version of matchers."""
        try:
            match_str = ", ".join([f'{k}="{v}"' for k, v in obj.matchers.items()])
            return format_html('<code style="font-size: 0.9em;">{}</code>', match_str[:100] + ('...' if len(match_str) > 100 else ''))
        except Exception:
            return "Invalid Matchers"
    display_matchers_short.short_description = "Matchers"

    def is_active_display(self, obj):
        """Boolean display for is_active method."""
        return obj.is_active()
    is_active_display.boolean = True
    is_active_display.short_description = "Active"

    def comment_short(self, obj):
        """Shortened comment."""
        return obj.comment[:75] + ('...' if len(obj.comment) > 75 else '')
    comment_short.short_description = "Comment"

    # Automatically set created_by on save from admin
    def save_model(self, request, obj, form, change):
        if not obj.pk: # Only set created_by on creation
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

