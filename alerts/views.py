from django.views.generic import TemplateView, ListView, DetailView, FormView
from django.db.models import Count, Q
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.http import JsonResponse
from django.contrib import messages
from django.views.generic.detail import SingleObjectMixin
import logging
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

from .models import AlertGroup, AlertInstance, AlertComment
from .forms import AlertAcknowledgementForm, AlertCommentForm
from .services.alerts_processor import acknowledge_alert
from docs.services.documentation_matcher import match_documentation_to_alert

logger = logging.getLogger(__name__)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'alerts/dashboard.html'
    
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
        logger.info(f"Viewing alert details for alert: {self.object.name} (ID: {self.object.id})")
        
        # Get linked documentation for this alert
        context['linked_documentation'] = self.object.documentation_links.select_related('documentation').all()
        
        # Get alert instances for history with pagination
        page = self.request.GET.get('page', 1)
        try:
            page = int(page)
        except (TypeError, ValueError):
            page = 1
            
        instances = self.object.instances.all().order_by('-started_at')
        paginator = Paginator(instances, 10)  # Show 10 instances per page
        
        try:
            instances = paginator.page(page)
        except PageNotAnInteger:
            instances = paginator.page(1)
        except EmptyPage:
            instances = paginator.page(paginator.num_pages)
            
        context['instances'] = instances
        
        # Get comments
        context['comments'] = self.object.comments.all().order_by('-created_at')
        
        # Add forms to context
        context['acknowledge_form'] = AlertAcknowledgementForm()
        context['comment_form'] = AlertCommentForm()
        
        # Format messages for JavaScript
        context['messages'] = [{'message': str(message), 'tags': message.tags} for message in messages.get_messages(self.request)]
        
        # Add active tab to context
        context['active_tab'] = self.request.GET.get('tab', 'details')
        
        return context
    
    def post(self, request, *args, **kwargs):
        alert = self.get_object()
        logger.info(f"Processing POST request for alert: {alert.name} (ID: {alert.id})")
        
        # Handle acknowledgement with required comment
        if 'acknowledge' in request.POST:
            form = AlertAcknowledgementForm(request.POST)
            if form.is_valid():
                comment_text = form.cleaned_data['comment']
                logger.info(f"Acknowledging alert: {alert.name} with comment: {comment_text}")
                
                # Create the comment first
                AlertComment.objects.create(
                    alert_group=alert,
                    user=request.user,
                    content=comment_text
                )
                
                # Then acknowledge the alert
                acknowledge_alert(alert, request.user)
                
                messages.success(request, "Alert has been acknowledged successfully.")
                return redirect('alerts:alert-detail', fingerprint=alert.fingerprint)
            else:
                logger.warning(f"Invalid acknowledgement form for alert: {alert.name}")
                messages.error(request, "Please provide a comment when acknowledging an alert.")
                return self.get(request, *args, **kwargs)
        
        # Handle comment
        if 'comment' in request.POST:
            form = AlertCommentForm(request.POST)
            if form.is_valid():
                comment = form.save(commit=False)
                comment.alert_group = alert
                comment.user = request.user
                comment.save()
                logger.info(f"Added new comment to alert: {alert.name}")
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'success',
                        'user': request.user.username,
                        'content': form.cleaned_data['content']
                    })
                else:
                    messages.success(request, "Comment added successfully.")
                    return redirect('alerts:alert-detail', fingerprint=alert.fingerprint)
            else:
                logger.warning(f"Invalid comment form for alert: {alert.name}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
                else:
                    messages.error(request, "Please provide a valid comment.")
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