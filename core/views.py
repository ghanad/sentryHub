from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from alerts.models import AlertGroup
from django.db.models.functions import TruncHour

class HomeView(TemplateView):
    template_name = 'core/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any context data needed for the home page
        return context

class AboutView(TemplateView):
    template_name = 'core/about.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any context data needed for the about page
        return context

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get total alerts count
        context['total_alerts'] = AlertGroup.objects.count()
        
        # Get currently firing alerts (status = 'firing')
        context['firing_alerts'] = AlertGroup.objects.filter(current_status='firing').count()
        
        # Get unacknowledged alerts
        context['unacknowledged_alerts'] = AlertGroup.objects.filter(
            current_status='firing',
            acknowledged=False
        ).count()
        
        # Get recent alerts (last 10)
        context['recent_alerts'] = AlertGroup.objects.order_by('-last_occurrence')[:10]
        
        # Get alert statistics by severity
        context['severity_stats'] = AlertGroup.objects.values('severity').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Get alert statistics by status
        context['status_stats'] = AlertGroup.objects.values('current_status').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Get alert trends over time (last 24 hours)
        last_24h = timezone.now() - timedelta(hours=24)
        context['alert_trends'] = AlertGroup.objects.filter(
            last_occurrence__gte=last_24h
        ).annotate(
            hour=TruncHour('last_occurrence')
        ).values('hour').annotate(
            count=Count('id')
        ).order_by('hour')
        
        return context 