from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from alerts.models import AlertGroup
from django.db.models.functions import TruncHour
from django.shortcuts import redirect

class HomeView(LoginRequiredMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        # Redirect to alerts dashboard
        return redirect('dashboard:dashboard')

class AboutView(TemplateView):
    template_name = 'core/about.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any context data needed for the about page
        return context
