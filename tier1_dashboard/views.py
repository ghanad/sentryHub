# Path: tier1_dashboard/views.py
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q, Case, When, Value, IntegerField
from alerts.models import AlertGroup
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
            acknowledged=False
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
