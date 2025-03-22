from django.contrib import admin
from .models import AlertGroup, AlertInstance, AlertComment, AlertAcknowledgementHistory


@admin.register(AlertGroup)
class AlertGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'instance', 'fingerprint', 'severity', 
                    'current_status', 'total_firing_count', 
                    'first_occurrence', 'last_occurrence', 'acknowledged')
    list_filter = ('severity', 'current_status', 'acknowledged')
    search_fields = ('name', 'fingerprint', 'instance')
    date_hierarchy = 'first_occurrence'


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