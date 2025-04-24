from django.shortcuts import render
from django.views.generic import TemplateView
from django.db.models import Count, Q
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from datetime import timedelta
import logging
import json
from alerts.models import AlertGroup
from alerts.views import AlertListView
from alerts.forms import AlertAcknowledgementForm

logger = logging.getLogger(__name__)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/main_page.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # --- 1. Calculate Stats for Cards ---
        active_alerts_qs = AlertGroup.objects.filter(current_status='firing')
        silenced_alerts_qs = AlertGroup.objects.filter(is_silenced=True) # Count all defined silenced alerts

        context['total_firing_alerts'] = active_alerts_qs.count()
        # Unacknowledged = Firing AND NOT Acknowledged AND NOT Silenced
        context['unacknowledged_alerts'] = active_alerts_qs.filter(
            acknowledged=False,
            is_silenced=False # Exclude silenced alerts from needing acknowledgement
        ).count()
        context['silenced_alerts'] = silenced_alerts_qs.count()

        # --- 2. Data for Severity Donut Chart ---
        severity_distribution = active_alerts_qs.values('severity').annotate(count=Count('severity')).order_by('severity')
        sev_labels = []
        sev_data = []
        sev_map = {'critical': 0, 'warning': 0, 'info': 0}
        for item in severity_distribution:
            sev_map[item['severity']] = item['count']
        # Ensure order for the chart
        sev_labels = ['Critical', 'Warning', 'Info']
        sev_data = [sev_map['critical'], sev_map['warning'], sev_map['info']]

        context['severity_distribution_json'] = json.dumps({
            'labels': sev_labels,
            'data': sev_data
        })

        # --- 3. Data for Instance Donut Chart (Top 5) ---
        instance_distribution = active_alerts_qs.exclude(instance__isnull=True).exclude(instance__exact='').values('instance').annotate(count=Count('id')).order_by('-count')[:10] # Get top 10
        inst_labels = [item['instance'] for item in instance_distribution]
        inst_data = [item['count'] for item in instance_distribution]

        context['instance_distribution_json'] = json.dumps({
            'labels': inst_labels,
            'data': inst_data
        })

        # --- 4. Data for Daily Trend Bar Chart (Last 7 Days) ---
        # Note: This counts alerts occurred (first_occurrence) in the last 7 days, NOT currently active ones. Adjust if needed.
        seven_days_ago = timezone.now().date() - timedelta(days=6)
        daily_alerts = AlertGroup.objects.filter(
            first_occurrence__date__gte=seven_days_ago
        ).values('first_occurrence__date', 'severity').annotate(count=Count('id')).order_by('first_occurrence__date')

        # Process data for stacked bar chart format
        trend_data = {} # {date_str: {'Critical': count, 'Warning': count, 'Info': count}}
        dates = [(seven_days_ago + timedelta(days=i)) for i in range(7)]
        date_labels = [d.strftime('%a') for d in dates] # Mon, Tue, etc.

        for d in dates:
            trend_data[d.isoformat()] = {'Critical': 0, 'Warning': 0, 'Info': 0}

        for alert in daily_alerts:
            date_str = alert['first_occurrence__date'].isoformat()
            severity = alert['severity'].capitalize() # Match chart labels
            if date_str in trend_data and severity in trend_data[date_str]:
                trend_data[date_str][severity] = alert['count']

        daily_datasets = [
            {'label': 'Critical', 'data': [trend_data[d.isoformat()]['Critical'] for d in dates]},
            {'label': 'Warning', 'data': [trend_data[d.isoformat()]['Warning'] for d in dates]},
            {'label': 'Info', 'data': [trend_data[d.isoformat()]['Info'] for d in dates]},
        ]

        context['daily_trend_json'] = json.dumps({
            'labels': date_labels,
            'datasets': daily_datasets
        })

        # --- 5. Data for Recent Alerts Table (Top 5 Firing) ---
        context['recent_alerts'] = active_alerts_qs.order_by('-last_occurrence')[:5]

        return context


class Tier1AlertListView(AlertListView):
    """List view of unacknowledged alerts for Tier 1 users"""
    paginate_by = None  # Disable pagination
    template_name = 'dashboard/tier1_unacked.html'

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
