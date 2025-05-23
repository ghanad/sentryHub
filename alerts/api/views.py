from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework.permissions import AllowAny
import logging
import requests
import json # Keep json import

from ..models import AlertGroup, AlertInstance, AlertComment
from ..services.alerts_processor import acknowledge_alert
from ..services.alert_logger import save_alert_to_file
# Import the task for .delay()
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
        # logger.info(f"Received webhook data: {request.data}")
        # Validate the data structure first
        serializer = AlertmanagerWebhookSerializer(data=request.data) 

        if serializer.is_valid():
            # Explicitly serialize the payload to JSON before sending
            try:
                payload_json = json.dumps(request.data)
                logger.info("Webhook serializer valid. Calling Celery task with JSON payload...")
                process_alert_payload_task.delay(payload_json)
                return Response({'status': 'success (task queued)'}, status=status.HTTP_200_OK)
            except TypeError as e:
                 logger.error(f"Could not serialize payload to JSON: {e}", exc_info=True)
                 return Response({'status': 'error serializing payload'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # --- Direct Call Test (Commented Out) ---
            # logger.info("Webhook serializer valid. Attempting DIRECT task function call...")
            # try:
            #     result = process_alert_payload_task(serializer.validated_data) 
            #     logger.info(f"Direct task function call completed. Result: {result}")
            #     return Response({'status': 'success (direct call test)'}, status=status.HTTP_200_OK)
            # except Exception as e:
            #      logger.error(f"Error during DIRECT task function call: {e}", exc_info=True)
            #      return Response({'status': 'error during direct call'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            # --- End Direct Call Test ---

        logger.warning(f"Webhook serializer invalid: {serializer.errors}")
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

        # Only show active (firing) alerts by default, unless a specific status filter is applied
        active_only = self.request.query_params.get('active_only', 'true')
        if active_only.lower() == 'true' and not status_filter: # Apply only if no status filter
            queryset = queryset.filter(current_status='firing')

        # Filter by instance
        instance = self.request.query_params.get('instance', None)
        if instance:
            queryset = queryset.filter(instance__icontains=instance)

        # Filter by service (within labels JSONField)
        service = self.request.query_params.get('service', None)
        if service:
            queryset = queryset.filter(labels__service__icontains=service)

        # Filter by job (within labels JSONField)
        job = self.request.query_params.get('job', None)
        if job:
            queryset = queryset.filter(labels__job__icontains=job)

        # Filter by cluster (within labels JSONField)
        cluster = self.request.query_params.get('cluster', None)
        if cluster:
            queryset = queryset.filter(labels__cluster__icontains=cluster)

        # Filter by namespace (within labels JSONField)
        namespace = self.request.query_params.get('namespace', None)
        if namespace:
            queryset = queryset.filter(labels__namespace__icontains=namespace)

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
        if start_date:
            queryset = queryset.filter(started_at__gte=start_date)

        end_date = self.request.query_params.get('end_date', None)
        if end_date:
            queryset = queryset.filter(started_at__lte=end_date)

        return queryset
