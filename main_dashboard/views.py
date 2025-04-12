from django.shortcuts import render
from django.views.generic import TemplateView

import logging

class DashboardView(TemplateView):
    template_name = 'main_dashboard/dashboard.html'
logger = logging.getLogger(__name__)
