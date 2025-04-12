# docs/api/serializers.py

from rest_framework import serializers
from ..models import AlertDocumentation, DocumentationAlertGroup


class AlertDocumentationSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = AlertDocumentation
        fields = [
            'id', 'title', 'description', 
            'created_at', 'updated_at', 'created_by', 'created_by_name'
        ]
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None


class DocumentationAlertGroupSerializer(serializers.ModelSerializer):
    documentation_details = serializers.SerializerMethodField()
    alert_group_details = serializers.SerializerMethodField()
    linked_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = DocumentationAlertGroup
        fields = [
            'id', 'documentation', 'alert_group', 'linked_at', 'linked_by',
            'documentation_details', 'alert_group_details', 'linked_by_name'
        ]
    
    def get_documentation_details(self, obj):
        return {
            'id': obj.documentation.id,
            'title': obj.documentation.title
        }
    
    def get_alert_group_details(self, obj):
        return {
            'id': obj.alert_group.id,
            'name': obj.alert_group.name,
            'fingerprint': obj.alert_group.fingerprint,
            'current_status': obj.alert_group.current_status
        }
    
    def get_linked_by_name(self, obj):
        if obj.linked_by:
            return obj.linked_by.get_full_name() or obj.linked_by.username
        return None