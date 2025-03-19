from rest_framework import serializers
from ..models import AlertGroup, AlertInstance, AlertComment


class AlertInstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertInstance
        fields = ['id', 'status', 'started_at', 'ended_at', 'annotations', 'generator_url']


class AlertGroupSerializer(serializers.ModelSerializer):
    instances = AlertInstanceSerializer(many=True, read_only=True)
    acknowledged_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = AlertGroup
        fields = ['id', 'fingerprint', 'name', 'labels', 'severity', 'first_occurrence', 
                 'last_occurrence', 'current_status', 'total_firing_count', 
                 'acknowledged', 'acknowledged_by', 'acknowledged_by_name', 
                 'acknowledgement_time', 'instances']
    
    def get_acknowledged_by_name(self, obj):
        if obj.acknowledged_by:
            return obj.acknowledged_by.get_full_name() or obj.acknowledged_by.username
        return None


class AlertCommentSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = AlertComment
        fields = ['id', 'alert_group', 'user', 'user_name', 'content', 'created_at']
    
    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


class AlertmanagerWebhookSerializer(serializers.Serializer):
    receiver = serializers.CharField(required=True)
    status = serializers.CharField(required=True)
    alerts = serializers.ListField(required=True)
    groupLabels = serializers.DictField(required=False)
    commonLabels = serializers.DictField(required=False)
    commonAnnotations = serializers.DictField(required=False)
    externalURL = serializers.URLField(required=False)
    version = serializers.CharField(required=False)
    groupKey = serializers.CharField(required=False)


class AcknowledgeAlertSerializer(serializers.Serializer):
    acknowledged = serializers.BooleanField(required=True)
    comment = serializers.CharField(required=True)