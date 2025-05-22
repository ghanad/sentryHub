from rest_framework import serializers
from ..models import AlertGroup, AlertInstance, AlertComment, AlertAcknowledgementHistory


class AlertInstanceSerializer(serializers.ModelSerializer):
    alert_group_fingerprint = serializers.SerializerMethodField()

    class Meta:
        model = AlertInstance
        fields = ['id', 'status', 'started_at', 'ended_at', 'annotations', 'generator_url', 'alert_group_fingerprint']

    def get_alert_group_fingerprint(self, obj):
        return obj.alert_group.fingerprint if obj.alert_group else None


class AlertAcknowledgementHistorySerializer(serializers.ModelSerializer):
    acknowledged_by_name = serializers.SerializerMethodField()
    instance_details = serializers.SerializerMethodField()
    
    class Meta:
        model = AlertAcknowledgementHistory
        fields = ['id', 'acknowledged_by', 'acknowledged_by_name', 'acknowledged_at', 
                  'comment', 'alert_instance', 'instance_details']
    
    def get_acknowledged_by_name(self, obj):
        if obj.acknowledged_by:
            return obj.acknowledged_by.get_full_name() or obj.acknowledged_by.username
        return None
    
    def get_instance_details(self, obj):
        if obj.alert_instance:
            return {
                'id': obj.alert_instance.id,
                'started_at': obj.alert_instance.started_at,
                'ended_at': obj.alert_instance.ended_at,
                'status': obj.alert_instance.status
            }
        return None


class AlertGroupSerializer(serializers.ModelSerializer):
    instances = AlertInstanceSerializer(many=True, read_only=True)
    acknowledged_by_name = serializers.SerializerMethodField()
    acknowledgement_history = AlertAcknowledgementHistorySerializer(many=True, read_only=True)
    
    class Meta:
        model = AlertGroup
        fields = ['id', 'fingerprint', 'name', 'labels', 'severity', 
                 'instance', 'first_occurrence', 'last_occurrence', 'current_status', 
                 'total_firing_count', 'acknowledged', 'acknowledged_by', 
                 'acknowledged_by_name', 'acknowledgement_time', 'instances',
                 'acknowledgement_history']
    
    def get_acknowledged_by_name(self, obj):
        if obj.acknowledged_by:
            return obj.acknowledged_by.get_full_name() or obj.acknowledged_by.username
        return None


class AlertCommentSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = AlertComment
        fields = ['id', 'user_name', 'content', 'created_at']
        read_only_fields = ['alert_group', 'user'] # These are set by the view
    
    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


class AlertmanagerWebhookSerializer(serializers.Serializer):
    receiver = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    alerts = serializers.ListField(required=True)
    groupLabels = serializers.DictField(required=False)
    commonLabels = serializers.DictField(required=False)
    commonAnnotations = serializers.DictField(required=False)
    externalURL = serializers.CharField(required=False)
    version = serializers.CharField(required=False)
    groupKey = serializers.CharField(required=False)
    truncatedAlerts = serializers.IntegerField(required=False)


class AcknowledgeAlertSerializer(serializers.Serializer):
    acknowledged = serializers.BooleanField(required=True)
    comment = serializers.CharField(required=True)