# docs/admin.py

from django.contrib import admin
from .models import AlertDocumentation, DocumentationAlertGroup


class DocumentationAlertGroupInline(admin.TabularInline):
    model = DocumentationAlertGroup
    extra = 0
    readonly_fields = ('alert_group', 'linked_at', 'linked_by')
    can_delete = False


@admin.register(AlertDocumentation)
class AlertDocumentationAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    fields = (
        'title', 'description',
        ('created_at', 'updated_at', 'created_by')
    )
    inlines = [DocumentationAlertGroupInline]
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating a new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(DocumentationAlertGroup)
class DocumentationAlertGroupAdmin(admin.ModelAdmin):
    list_display = ('documentation', 'alert_group', 'linked_at', 'linked_by')
    list_filter = ('linked_at',)
    search_fields = ('documentation__title', 'alert_group__name')
    readonly_fields = ('linked_at',)
    date_hierarchy = 'linked_at'