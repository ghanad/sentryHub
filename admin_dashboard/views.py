# Path: admin_dashboard/views.py

from django.views.generic import TemplateView, ListView
from django.contrib.auth.mixins import UserPassesTestMixin
from alerts.models import AlertComment, AlertAcknowledgementHistory
from django.utils import timezone
from django.contrib.auth.models import User

class AdminRequiredMixin(UserPassesTestMixin):
    """
    Mixin to ensure only admin users can access the view.
    In the future, this could be enhanced with more specific role-checking.
    """
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff

# class AdminDashboardView(AdminRequiredMixin, TemplateView):
    """
    Main admin dashboard view. Will display admin statistics and links to admin sections.
    """
    template_name = 'admin_dashboard/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get some basic stats for the dashboard
        context['total_comments'] = AlertComment.objects.count()
        context['total_users'] = User.objects.count()
        context['total_acknowledgements'] = AlertAcknowledgementHistory.objects.count()
        context['recent_comments'] = AlertComment.objects.order_by('-created_at')[:5]
        context['recent_acknowledgements'] = AlertAcknowledgementHistory.objects.select_related('alert_group', 'acknowledged_by').order_by('-acknowledged_at')[:5]
        
        return context

# class AdminCommentsView(AdminRequiredMixin, ListView):
    """
    View to display all comments for admin review.
    """
    model = AlertComment
    template_name = 'admin_dashboard/comments.html'
    context_object_name = 'comments'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = AlertComment.objects.all().select_related('user', 'alert_group').order_by('-created_at')
        
        # Apply filters if provided
        user_filter = self.request.GET.get('user')
        if user_filter:
            queryset = queryset.filter(user__username__icontains=user_filter)
        
        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        
        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)
        
        alert_filter = self.request.GET.get('alert')
        if alert_filter:
            queryset = queryset.filter(alert_group__name__icontains=alert_filter)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter parameters to context
        context['user_filter'] = self.request.GET.get('user', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        context['alert_filter'] = self.request.GET.get('alert', '')
        
        return context

# class AdminAcknowledgementsView(AdminRequiredMixin, ListView):
    """
    View to display all acknowledgements for admin review.
    """
    model = AlertAcknowledgementHistory
    template_name = 'admin_dashboard/acknowledgements.html'
    context_object_name = 'acknowledgements'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = AlertAcknowledgementHistory.objects.all().select_related(
            'alert_group', 
            'alert_instance', 
            'acknowledged_by'
        ).order_by('-acknowledged_at')
        
        # Apply filters if provided
        user_filter = self.request.GET.get('user')
        if user_filter:
            queryset = queryset.filter(acknowledged_by__username__icontains=user_filter)
        
        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(acknowledged_at__gte=date_from)
        
        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(acknowledged_at__lte=date_to)
        
        alert_filter = self.request.GET.get('alert')
        if alert_filter:
            queryset = queryset.filter(alert_group__name__icontains=alert_filter)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter parameters to context
        context['user_filter'] = self.request.GET.get('user', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        context['alert_filter'] = self.request.GET.get('alert', '')
        
        return context