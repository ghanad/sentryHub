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

