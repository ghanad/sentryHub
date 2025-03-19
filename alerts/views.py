from django.views.generic import TemplateView, ListView, DetailView
from django.db.models import Count, Q
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.http import JsonResponse

from .models import AlertGroup, AlertInstance


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'alerts/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get alert statistics
        context['total_alerts'] = AlertGroup.objects.count()
        context['active_alerts'] = AlertGroup.objects.filter(current_status='firing').count()
        
        # Get alerts by severity
        severity_counts = AlertGroup.objects.filter(
            current_status='firing'
        ).values('severity').annotate(count=Count('severity'))
        
        context['severity_counts'] = {
            item['severity']: item['count'] for item in severity_counts
        }
        
        # Get recent alerts
        context['recent_alerts'] = AlertGroup.objects.filter(
            current_status='firing'
        ).order_by('-last_occurrence')[:10]
        
        return context


class AlertListView(LoginRequiredMixin, ListView):
    model = AlertGroup
    template_name = 'alerts/alert_list.html'
    context_object_name = 'alerts'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = AlertGroup.objects.all()
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(current_status=status)
        else:
            # Default to showing only firing alerts
            queryset = queryset.filter(current_status='firing')
        
        # Filter by severity
        severity = self.request.GET.get('severity')
        if severity:
            queryset = queryset.filter(severity=severity)
        
        # Filter by acknowledgement status
        acknowledged = self.request.GET.get('acknowledged')
        if acknowledged == 'true':
            queryset = queryset.filter(acknowledged=True)
        elif acknowledged == 'false':
            queryset = queryset.filter(acknowledged=False)
        
        # Search by name or fingerprint
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(fingerprint__icontains=search)
            )
        
        return queryset.order_by('-last_occurrence')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter parameters to context
        context['status'] = self.request.GET.get('status', '')
        context['severity'] = self.request.GET.get('severity', '')
        context['acknowledged'] = self.request.GET.get('acknowledged', '')
        context['search'] = self.request.GET.get('search', '')
        
        return context


class AlertDetailView(LoginRequiredMixin, DetailView):
    model = AlertGroup
    template_name = 'alerts/alert_detail.html'
    context_object_name = 'alert'
    slug_field = 'fingerprint'
    slug_url_kwarg = 'fingerprint'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get alert instances for history
        context['instances'] = self.object.instances.all().order_by('-started_at')
        
        # Get comments
        context['comments'] = self.object.comments.all().order_by('-created_at')
        
        return context
    
    def post(self, request, *args, **kwargs):
        alert = self.get_object()
        
        # Handle acknowledgement
        if 'acknowledge' in request.POST:
            from .services.alerts_processor import acknowledge_alert
            acknowledge_alert(alert, request.user)
            return redirect('alerts:alert-detail', fingerprint=alert.fingerprint)
        
        # Handle comment
        if 'comment' in request.POST and request.POST.get('content'):
            from .models import AlertComment
            AlertComment.objects.create(
                alert_group=alert,
                user=request.user,
                content=request.POST.get('content')
            )
            return redirect('alerts:alert-detail', fingerprint=alert.fingerprint)
        
        return redirect('alerts:alert-detail', fingerprint=alert.fingerprint)


class AlertHistoryView(LoginRequiredMixin, DetailView):
    model = AlertGroup
    template_name = 'alerts/alert_history.html'
    context_object_name = 'alert'
    slug_field = 'fingerprint'
    slug_url_kwarg = 'fingerprint'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all instances for this alert group
        context['instances'] = self.object.instances.all().order_by('-started_at')
        
        return context