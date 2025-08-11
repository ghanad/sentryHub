import json
from django.contrib import admin
from django.utils.html import format_html
from .models import JiraIntegrationRule, SlackIntegrationRule, PhoneBook, SmsIntegrationRule

@admin.register(JiraIntegrationRule)
class JiraIntegrationRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'priority', 'jira_project_key',
                   'jira_issue_type', 'updated_at')
    list_filter = ('is_active', 'jira_project_key', 'jira_issue_type')
    search_fields = ('name', 'jira_project_key') # Removed 'description'
    ordering = ('-priority', 'name')
    readonly_fields = ('created_at', 'updated_at', 'get_match_criteria_preview')

    fieldsets = (
        (None, {
            'fields': ('name', 'is_active', 'priority') # Removed 'description'
        }),
        ('Jira Configuration', {
            'fields': ('jira_project_key', 'jira_issue_type') # REMOVED template fields from here
        }),
        ('Match Criteria', {
            'fields': ('match_criteria', 'get_match_criteria_preview'),
            'description': 'JSON object defining label match criteria. E.g. {"job": "node", "severity": "critical"}' # Kept description here
        }),
        # Added Jira Templates section for clarity in admin
        ('Jira Issue Templates', {
             'fields': ('jira_title_template', 'jira_description_template', 'jira_update_comment_template'),
             'classes': ('collapse',), # Optional: Collapse by default
             'description': 'Define templates for Jira issue content using Django template syntax (e.g., {{ labels.instance }}).'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_match_criteria_preview(self, obj):
        """Formatted preview of match criteria."""
        if not isinstance(obj.match_criteria, dict):
            return "Invalid JSON"
        try:
            pretty_json = json.dumps(obj.match_criteria, indent=2, ensure_ascii=False)
            return format_html('<pre style="white-space: pre-wrap; max-width: 400px;">{}</pre>', pretty_json)
        except Exception:
            return "Invalid JSON"
    get_match_criteria_preview.short_description = "Match Criteria Preview"


@admin.register(SlackIntegrationRule)
class SlackIntegrationRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'priority', 'slack_channel')
    list_filter = ('is_active', 'slack_channel')
    search_fields = ('name', 'slack_channel')
    ordering = ('-priority', 'name')


@admin.register(PhoneBook)
class PhoneBookAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number')
    search_fields = ('name',)


@admin.register(SmsIntegrationRule)
class SmsIntegrationRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'priority', 'use_sms_annotation')
    list_filter = ('is_active', 'use_sms_annotation')
    search_fields = ('name',)
    ordering = ('-priority', 'name')
