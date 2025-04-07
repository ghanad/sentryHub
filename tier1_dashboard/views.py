# Path: tier1_dashboard/views.py
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin # Removed UserPassesTestMixin
from django.db.models import Count, Q, Case, When, Value, IntegerField
from alerts.models import AlertGroup
from alerts.views import AlertListView # Import base AlertListView
import logging

logger = logging.getLogger(__name__)

class Tier1DashboardView(LoginRequiredMixin, ListView):
    """
    Dashboard view specifically for Tier 1 operators, showing active,
    unacknowledged alerts prioritized by severity and time.
    """
    model = AlertGroup
    template_name = 'tier1_dashboard/dashboard.html'
    context_object_name = 'alerts'
    # No pagination needed for this focused view, show all critical items.
    # paginate_by = 50 # Consider adding if list can become very long

    def get_queryset(self):
        """
        Returns only firing, unacknowledged alerts, sorted by severity then time.
        """
        severity_order = Case(
            When(severity='critical', then=Value(1)),
            When(severity='warning', then=Value(2)),
            When(severity='info', then=Value(3)),
            default=Value(4),
            output_field=IntegerField(),
        )
        queryset = AlertGroup.objects.filter(
            current_status='firing',
            acknowledged=False,
            is_silenced=False # <-- Add this filter to exclude silenced alerts
        ).annotate(
            severity_priority=severity_order
        ).order_by('severity_priority', '-last_occurrence')

        logger.info(f"Found {queryset.count()} active, unacknowledged alerts for Tier 1.")
        return queryset

    def get_context_data(self, **kwargs):
        """
        Adds alert counts to the context. (Removed count logic as per request)
        """
        context = super().get_context_data(**kwargs)
        # No additional context needed after removing summary cards
        return context


class Tier1AlertListView(AlertListView): # Inherit only from AlertListView (which already includes LoginRequiredMixin)
    """
    Provides a list view of unacknowledged alerts for Tier 1 users,
    without filtering options and with auto-refresh.
    Inherits filtering logic and base structure from alerts.views.AlertListView.
    """
    paginate_by = None  # Disable pagination
    template_name = 'tier1_dashboard/alert_list.html' # Specify the new template

    # Removed test_func - Access control temporarily disabled for testing

    def get_queryset(self):
        """
        Override to return only unacknowledged alerts, inheriting base ordering.
        """
        # Call the parent's get_queryset to get the base annotations and ordering
        base_queryset = super().get_queryset()
        # Apply the specific filter for this view
        return base_queryset.filter(acknowledged=False)

    def get_context_data(self, **kwargs):
        """
        Override to remove context variables related to filtering.
        """
        context = super().get_context_data(**kwargs)
        # Remove filter parameters from the context as they are not used in the template
        filter_keys = ['status', 'severity', 'instance', 'acknowledged', 'silenced_filter', 'search']
        for key in filter_keys:
            context.pop(key, None)
        # Also remove pagination related context if any exists from parent
        context.pop('paginator', None)
        context.pop('page_obj', None)
        context.pop('is_paginated', None)
        return context
