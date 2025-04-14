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
from ..services.alerts_processor import acknowledge_alert
from ..services.alert_logger import save_alert_to_file
from ..tasks import process_alert_payload_task
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
            # Process the entire payload asynchronously
            process_alert_payload_task.delay(serializer.validated_data)
            return Response({'status': 'success'}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AlertGroupViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows alert groups to be viewed.
    """
    queryset = AlertGroup.objects.all()
    serializer_class = AlertGroupSerializer
    lookup_field = 'fingerprint' # Use fingerprint instead of pk for detail routes
    # Removed 'service', 'job', 'cluster', 'namespace' as they are handled manually in get_queryset
    filterset_fields = ['severity', 'current_status', 'acknowledged', 'instance'] 
    search_fields = ['name', 'fingerprint', 'instance', 'service'] # Keep 'service' in search_fields if needed
    
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
        
        # Filter by instance
        instance = self.request.query_params.get('instance', None)
        if instance:
            queryset = queryset.filter(instance__icontains=instance)
        
        # Filter by service
        service = self.request.query_params.get('service', None)
        if service:
            queryset = queryset.filter(service__icontains=service)
        
        # Filter by job
        job = self.request.query_params.get('job', None)
        if job:
            queryset = queryset.filter(job__icontains=job)
        
        # Filter by cluster
        cluster = self.request.query_params.get('cluster', None)
        if cluster:
            queryset = queryset.filter(cluster__icontains=cluster)
        
        # Filter by namespace
        namespace = self.request.query_params.get('namespace', None)
        if namespace:
            queryset = queryset.filter(namespace__icontains=namespace)
        
        return queryset
    
    @action(detail=True, methods=['put'])
    def acknowledge(self, request, fingerprint=None): # Changed pk to fingerprint
        alert_group = self.get_object() # get_object() will now use fingerprint
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
                acknowledge_alert(alert_group, request.user, comment_text)
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
    def history(self, request, fingerprint=None): # Changed pk to fingerprint
        alert_group = self.get_object()
        instances = alert_group.instances.all()
        serializer = AlertInstanceSerializer(instances, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, fingerprint=None): # Changed pk to fingerprint
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
