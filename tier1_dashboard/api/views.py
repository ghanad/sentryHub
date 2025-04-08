# Path: tier1_dashboard/api/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.template.loader import render_to_string
from django.utils import timezone
from django.db.models import Case, When, Value, IntegerField, Max, Subquery, OuterRef, F
from django.db.models.functions import Coalesce
from alerts.models import AlertGroup, AlertInstance
import logging

logger = logging.getLogger(__name__)

class Tier1AlertDataAPIView(APIView):
    """
    API endpoint to fetch the latest Tier 1 alerts data (as HTML table rows)
    for automatic refresh.
    """
    permission_classes = [IsAuthenticated] # Use DRF permissions

    def get(self, request, *args, **kwargs):
        try:
            # Perform the same query as the main dashboard view
            severity_order = Case(
                When(severity='critical', then=Value(1)),
                When(severity='warning', then=Value(2)),
                When(severity='info', then=Value(3)),
                default=Value(4),
                output_field=IntegerField(),
            )
            # Subquery to get the minimum start time of active instances (for duration calculation)
            active_instances_subquery = AlertInstance.objects.filter(
                alert_group=OuterRef('pk'),
                status='firing'
            ).order_by('started_at').values('started_at')[:1]

            alerts = AlertGroup.objects.filter(
                # Remove this filter to show both firing and resolved unacknowledged alerts
                # current_status='firing',
                acknowledged=False,
                is_silenced=False
            ).annotate(
                severity_priority=severity_order,
                # Add annotations needed by the partial template to match the main view
                current_problem_start_time=Coalesce(
                    Subquery(active_instances_subquery),
                    None
                ),
                latest_instance_start=Max('instances__started_at')
            ).order_by('severity_priority', '-latest_instance_start') # Order by latest instance start like main view

            # Render the table rows using a partial template
            context = {'alerts': alerts, 'user': request.user} # Pass user for date formatting context
            html_content = render_to_string('tier1_dashboard/partials/_alert_table_rows.html', context)

            response_data = {
                'html': html_content,
                'timestamp': timezone.now().isoformat(),
                'alert_count': alerts.count(),
            }
            return Response(response_data)
        except Exception as e:
            logger.error(f"Error fetching Tier 1 alert data for API: {e}", exc_info=True)
            return Response({"error": "Failed to fetch alert data"}, status=500)
