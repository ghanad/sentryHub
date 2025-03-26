from django.views.generic import TemplateView
from django.db.models import Count, Q
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse, reverse_lazy
import logging
from alerts.models import AlertGroup

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
