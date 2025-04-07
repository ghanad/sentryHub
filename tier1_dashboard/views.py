from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse
from django.shortcuts import redirect
from alerts.models import AlertGroup, AlertComment
from alerts.views import AlertListView
from alerts.forms import AlertAcknowledgementForm, AlertCommentForm
from alerts.services.alerts_processor import acknowledge_alert
import logging

logger = logging.getLogger(__name__)

class Tier1AlertListView(AlertListView):
    """List view of unacknowledged alerts for Tier 1 users"""
    paginate_by = None  # Disable pagination
    template_name = 'tier1_dashboard/unack_alerts.html'

    def get_queryset(self):
        """Return only unacknowledged alerts"""
        base_queryset = super().get_queryset()
        return base_queryset.filter(acknowledged=False)

    def get_context_data(self, **kwargs):
        """Remove filter parameters and add acknowledgement form"""
        context = super().get_context_data(**kwargs)
        # Remove filter parameters
        filter_keys = ['status', 'severity', 'instance', 'acknowledged', 'silenced_filter', 'search']
        for key in filter_keys:
            context.pop(key, None)
        # Remove pagination context
        context.pop('paginator', None)
        context.pop('page_obj', None)
        context.pop('is_paginated', None)
        # Add the acknowledgement form
        context['acknowledge_form'] = AlertAcknowledgementForm()
        return context

class Tier1AlertDetailView(LoginRequiredMixin, DetailView):
    model = AlertGroup
    template_name = 'tier1_dashboard/alert_detail.html'
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
            
        # Get all instances ordered by started_at (newest first)
        all_instances = self.object.instances.all().order_by('-started_at')
        
        # Paginate for the history tab
        paginator = Paginator(all_instances, 10)
        try:
            paginated_instances = paginator.page(page)
        except PageNotAnInteger:
            paginated_instances = paginator.page(1)
        except EmptyPage:
            paginated_instances = paginator.page(paginator.num_pages)
            
        # For the details tab, we want the first instance (most recent)
        context['instances'] = paginated_instances
        context['last_instance'] = all_instances.first() if all_instances.exists() else None
        
        # Get acknowledgement history
        context['acknowledgement_history'] = self.object.acknowledgement_history.select_related(
            'acknowledged_by', 'alert_instance'
        ).order_by('-acknowledged_at')
        
        # Get comments
        comments_page = self.request.GET.get('comments_page', 1)
        try:
            comments_page = int(comments_page)
        except (TypeError, ValueError):
            comments_page = 1
            
        comments = self.object.comments.all().order_by('-created_at')
        comments_paginator = Paginator(comments, 10)  # 10 comments per page
        
        try:
            paginated_comments = comments_paginator.page(comments_page)
        except PageNotAnInteger:
            paginated_comments = comments_paginator.page(1)
        except EmptyPage:
            paginated_comments = comments_paginator.page(comments_paginator.num_pages)
            
        context['comments'] = paginated_comments
        
        # Add forms to context
        context['acknowledge_form'] = AlertAcknowledgementForm()
        context['comment_form'] = AlertCommentForm()
        
        # Add active tab to context
        context['active_tab'] = self.request.GET.get('tab', 'details')
        return context
    
    def post(self, request, *args, **kwargs):
        alert = self.get_object()
        logger.info(f"Processing POST request for alert: {alert.name} (ID: {alert.id})")
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

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
                acknowledge_alert(alert, request.user, comment_text)
                
                # Always redirect back to tier1 unacked alerts
                messages.success(request, "Alert has been acknowledged successfully.")
                return redirect('tier1_dashboard:tier1-unacked-alerts')
            else:
                logger.warning(f"Invalid acknowledgement form for alert: {alert.name}")
                messages.error(request, "Please provide a comment when acknowledging an alert.")
                context = self.get_context_data()
                context['acknowledge_form'] = form
                return self.render_to_response(context)

        # Handle comment
        if 'content' in request.POST:
            form = AlertCommentForm(request.POST)
            if form.is_valid():
                comment = form.save(commit=False)
                comment.alert_group = alert
                comment.user = request.user
                comment.save()
                logger.info(f"Added new comment to alert: {alert.name}")
                
                if is_ajax:
                    return JsonResponse({
                        'status': 'success',
                        'user': request.user.username,
                        'content': form.cleaned_data['content']
                    })
                else:
                    messages.success(request, "Comment added successfully.")
                    return redirect('tier1_dashboard:tier1-alert-detail', fingerprint=alert.fingerprint)
            else:
                logger.warning(f"Invalid comment form for alert: {alert.name}")
                if is_ajax:
                    return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
                else:
                    messages.error(request, "Please provide a valid comment.")
                    context = self.get_context_data()
                    context['comment_form'] = form
                    return self.render_to_response(context)

        return redirect('tier1_dashboard:tier1-alert-detail', fingerprint=alert.fingerprint)
