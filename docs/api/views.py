# docs/api/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q

from ..models import AlertDocumentation, DocumentationAlertGroup
from alerts.models import AlertGroup
from .serializers import AlertDocumentationSerializer, DocumentationAlertGroupSerializer
from ..services.documentation_matcher import match_documentation_to_alert


class DocumentationViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing alert documentation.
    """
    queryset = AlertDocumentation.objects.all()
    serializer_class = AlertDocumentationSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Apply search filter
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(description__icontains=search) |
                Q(actions__icontains=search) |
                Q(alert_name_pattern__icontains=search) |
                Q(tags__icontains=search)
            )
        
        # Apply severity filter
        severity = self.request.query_params.get('severity', None)
        if severity:
            queryset = queryset.filter(severity=severity)
        
        # Apply tags filter
        tags = self.request.query_params.get('tags', None)
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
            for tag in tag_list:
                queryset = queryset.filter(tags__icontains=tag)
        
        # Order by title by default
        return queryset.order_by('title')
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True)
    def linked_alerts(self, request, pk=None):
        """Get alerts linked to this documentation"""
        documentation = self.get_object()
        links = DocumentationAlertGroup.objects.filter(documentation=documentation)
        serializer = DocumentationAlertGroupSerializer(links, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def link_alert(self, request, pk=None):
        """Link an alert to this documentation"""
        documentation = self.get_object()
        alert_id = request.data.get('alert_id')
        
        if not alert_id:
            return Response(
                {'error': 'alert_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            alert_group = AlertGroup.objects.get(pk=alert_id)
        except AlertGroup.DoesNotExist:
            return Response(
                {'error': 'Alert not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        link, created = DocumentationAlertGroup.objects.get_or_create(
            documentation=documentation,
            alert_group=alert_group,
            defaults={'linked_by': request.user}
        )
        
        serializer = DocumentationAlertGroupSerializer(link)
        return Response(
            {
                'created': created,
                'link': serializer.data
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def unlink_alert(self, request, pk=None):
        """Unlink an alert from this documentation"""
        documentation = self.get_object()
        alert_id = request.data.get('alert_id')
        
        if not alert_id:
            return Response(
                {'error': 'alert_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            link = DocumentationAlertGroup.objects.get(
                documentation=documentation,
                alert_group_id=alert_id
            )
            link.delete()
            return Response({'status': 'success'})
        except DocumentationAlertGroup.DoesNotExist:
            return Response(
                {'error': 'Link not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class AlertDocumentationLinkViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing alert-documentation links.
    """
    queryset = DocumentationAlertGroup.objects.all()
    serializer_class = DocumentationAlertGroupSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by documentation
        documentation_id = self.request.query_params.get('documentation_id', None)
        if documentation_id:
            queryset = queryset.filter(documentation_id=documentation_id)
        
        # Filter by alert group
        alert_id = self.request.query_params.get('alert_id', None)
        if alert_id:
            queryset = queryset.filter(alert_group_id=alert_id)
        # Order by most recent link time, falling back to newest ID for ties
        return queryset.order_by('-linked_at', '-id')
