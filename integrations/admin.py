import json
from django.contrib import admin
from django.utils.html import format_html
from .models import JiraIntegrationRule, JiraRuleMatcher

@admin.register(JiraRuleMatcher)
class JiraRuleMatcherAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_criteria_preview', 'is_regex', 'created_at')
    search_fields = ('name', 'match_criteria')
    list_filter = ('is_regex',)
    readonly_fields = ('created_at', 'updated_at')

    def get_criteria_preview(self, obj):
        """Formatted preview of match criteria."""
        try:
            pretty_json = json.dumps(obj.match_criteria, indent=2, ensure_ascii=False)
            return format_html('<pre style="white-space: pre-wrap; max-width: 400px;">{}</pre>', pretty_json)
        except Exception:
            return "Invalid JSON"
    get_criteria_preview.short_description = "Match Criteria"

@admin.register(JiraIntegrationRule)
class JiraIntegrationRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'priority', 'jira_project_key',
                   'jira_issue_type', 'matcher_count', 'updated_at')
    list_filter = ('is_active', 'jira_project_key', 'jira_issue_type')
    search_fields = ('name', 'description', 'jira_project_key')
    ordering = ('-priority', 'name')
    filter_horizontal = ('matchers',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'is_active', 'priority')
        }),
        ('Jira Configuration', {
            'fields': ('jira_project_key', 'jira_issue_type')
        }),
        ('Matchers', {
            'fields': ('matchers',),
            'description': 'Rule matches if ALL selected matchers apply'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def matcher_count(self, obj):
        return obj.matchers.count()
    matcher_count.short_description = "# Matchers"
