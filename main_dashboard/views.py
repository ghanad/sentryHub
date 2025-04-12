from django.shortcuts import render
from django.views.generic import TemplateView
import logging

logger = logging.getLogger(__name__)

class DashboardView(TemplateView):
    template_name = 'main_dashboard/dashboard.html'
