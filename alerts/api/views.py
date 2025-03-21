from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework.permissions import AllowAny
import logging
import requests

from ..models import AlertGroup, AlertInstance, AlertComment
from ..services.alerts_processor import process_alert, acknowledge_alert
from ..services.alert_logger import save_alert_to_file
from .serializers import (
    AlertGroupSerializer, 
    AlertInstanceSerializer, 
    AlertCommentSerializer,
    AlertmanagerWebhookSerializer,
    AcknowledgeAlertSerializer
)

logger = logging.getLogger(__name__)

class AlertWebhookView(APIView):
    """
    API endpoint that receives alerts from Alertmanager.
    """
    permission_classes = [AllowAny]
    def post(self, request, format=None):
        logger.info(f"Received webhook data: {request.data}")
        serializer = AlertmanagerWebhookSerializer(data=request.data)
        
        if serializer.is_valid():
            # استخراج همه هشدارها
            alerts = serializer.validated_data['alerts']
            
            # هشدارها را براساس fingerprint گروه‌بندی می‌کنیم تا هشدارهای مرتبط با هم را با هم پردازش کنیم
            alerts_by_fingerprint = {}
            for alert in alerts:
                fingerprint = alert.get('fingerprint')
                if fingerprint not in alerts_by_fingerprint:
                    alerts_by_fingerprint[fingerprint] = []
                alerts_by_fingerprint[fingerprint].append(alert)
            
            # پردازش هشدارها به ترتیب fingerprint
            for fingerprint, fingerprint_alerts in alerts_by_fingerprint.items():
                # مرتب‌سازی هشدارها: اول resolved، سپس firing
                sorted_alerts = sorted(fingerprint_alerts, key=lambda a: 0 if a['status'] == 'resolved' else 1)
                
                # پردازش هر هشدار به ترتیب
                for alert_data in sorted_alerts:
                    process_alert(alert_data)
            
            return Response({'status': 'success'}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AlertGroupViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows alert groups to be viewed.
    """
    queryset = AlertGroup.objects.all()
    serializer_class = AlertGroupSerializer
    filterset_fields = ['severity', 'current_status', 'acknowledged']
    search_fields = ['name', 'fingerprint']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by current status if specified in query params
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(current_status=status_filter)
        
        # Only show active (firing) alerts by default
        active_only = self.request.query_params.get('active_only', 'true')
        if active_only.lower() == 'true':
            queryset = queryset.filter(current_status='firing')
        
        return queryset
    
    @action(detail=True, methods=['put'])
    def acknowledge(self, request, pk=None):
        alert_group = self.get_object()
        serializer = AcknowledgeAlertSerializer(data=request.data)
        
        if serializer.is_valid():
            comment_text = serializer.validated_data['comment']
            
            if serializer.validated_data['acknowledged']:
                # First, create the comment
                AlertComment.objects.create(
                    alert_group=alert_group,
                    user=request.user,
                    content=comment_text
                )
                
                # Then, acknowledge the alert
                acknowledge_alert(alert_group, request.user)
                return Response({
                    'status': 'success',
                    'message': 'Alert acknowledged successfully with comment'
                })
            else:
                alert_group.acknowledged = False
                alert_group.save()
                
                # Add a comment about un-acknowledging
                AlertComment.objects.create(
                    alert_group=alert_group,
                    user=request.user,
                    content=f"Alert un-acknowledged: {comment_text}"
                )
                
                return Response({
                    'status': 'success',
                    'message': 'Alert un-acknowledged successfully with comment'
                })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        alert_group = self.get_object()
        instances = alert_group.instances.all()
        serializer = AlertInstanceSerializer(instances, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        alert_group = self.get_object()
        
        if request.method == 'GET':
            comments = alert_group.comments.all()
            serializer = AlertCommentSerializer(comments, many=True)
            return Response(serializer.data)
        
        elif request.method == 'POST':
            serializer = AlertCommentSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(alert_group=alert_group, user=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AlertHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows alert instances to be viewed.
    """
    queryset = AlertInstance.objects.all()
    serializer_class = AlertInstanceSerializer
    filterset_fields = ['status']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by alert group fingerprint
        fingerprint = self.request.query_params.get('fingerprint', None)
        if fingerprint:
            queryset = queryset.filter(alert_group__fingerprint=fingerprint)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        
        if start_date:
            queryset = queryset.filter(started_at__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(started_at__lte=end_date)
        
        return queryset