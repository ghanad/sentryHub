from django.views.generic import TemplateView, ListView, DetailView, FormView
from django.db.models import Count, Q
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.http import JsonResponse
from django.contrib import messages
from django.views.generic.detail import SingleObjectMixin
import logging
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm

from alerts.models import AlertGroup, AlertInstance, AlertComment
from docs.services.documentation_matcher import match_documentation_to_alert

logger = logging.getLogger(__name__)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'main_dashboard/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get alert statistics
        context['total_alerts'] = AlertGroup.objects.count()
        context['active_alerts'] = AlertGroup.objects.filter(current_status='firing').count()
        context['unacknowledged_alerts'] = AlertGroup.objects.filter(
            current_status='firing',
            acknowledged=False
        ).count()
        
        # Get alerts by severity
        severity_counts = AlertGroup.objects.filter(
            current_status='firing'
        ).values('severity').annotate(count=Count('severity'))
        
        context['severity_counts'] = {
            item['severity']: item['count'] for item in severity_counts
        }
        
        # Get instance statistics
        context['instance_count'] = AlertGroup.objects.filter(
            current_status='firing'
        ).exclude(instance__isnull=True).values('instance').distinct().count()
        
        # Get top instances with most alerts
        top_instances = AlertGroup.objects.filter(
            current_status='firing'
        ).exclude(instance__isnull=True).values('instance').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        context['top_instances'] = top_instances
        
        # Get recent alerts
        context['recent_alerts'] = AlertGroup.objects.filter(
            current_status='firing'
        ).order_by('-last_occurrence')[:10]
        
        return context