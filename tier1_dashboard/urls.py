# Path: tier1_dashboard/urls.py
from django.urls import path, include
from .views import Tier1AlertListView # Removed Tier1DashboardView import
from .api.views import Tier1AlertDataAPIView # Assuming api views are in api/views.py

app_name = 'tier1_dashboard'

urlpatterns = [
    # Removed path for the old Tier1DashboardView
    # New path for the unacknowledged alerts list view
    path(
        'unacked/', # Shortened path
        Tier1AlertListView.as_view(),
        name='tier1-unacked-alerts' # Shortened name
    ),
    # API endpoint for auto-refresh (potentially for the main dashboard)
    path('api/alerts/', Tier1AlertDataAPIView.as_view(), name='api_alert_data'),
]
