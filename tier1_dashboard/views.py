# Path: tier1_dashboard/views.py
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin # Removed UserPassesTestMixin
from django.db.models import Count, Q, Case, When, Value, IntegerField
from alerts.models import AlertGroup
from alerts.views import AlertListView # Import base AlertListView
from alerts.forms import AlertAcknowledgementForm # Import the acknowledgement form
import logging

logger = logging.getLogger(__name__)

# Removed the old Tier1DashboardView class
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
        Override to remove context variables related to filtering and add the acknowledgement form.
        """
        context = super().get_context_data(**kwargs)
        # Remove filter parameters from the context
        filter_keys = ['status', 'severity', 'instance', 'acknowledged', 'silenced_filter', 'search']
        for key in filter_keys:
            context.pop(key, None)
        # Remove pagination context
        context.pop('paginator', None)
        context.pop('page_obj', None)
        context.pop('is_paginated', None)

        # Add the acknowledgement form to the context
        context['acknowledge_form'] = AlertAcknowledgementForm()
        return context
