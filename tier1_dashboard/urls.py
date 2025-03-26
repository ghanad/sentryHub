# Path: tier1_dashboard/urls.py
from django.urls import path, include
from .views import Tier1DashboardView
from .api.views import Tier1AlertDataAPIView # Assuming api views are in api/views.py

app_name = 'tier1_dashboard'

urlpatterns = [
    path('', Tier1DashboardView.as_view(), name='dashboard'),
    # API endpoint for auto-refresh
    path('api/alerts/', Tier1AlertDataAPIView.as_view(), name='api_alert_data'),
]
