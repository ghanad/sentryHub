# Path: tier1_dashboard/urls.py
from django.urls import path, include
from .views import Tier1DashboardView, Tier1AlertListView # Import the new view
from .api.views import Tier1AlertDataAPIView # Assuming api views are in api/views.py

app_name = 'tier1_dashboard'

urlpatterns = [
    path('', Tier1DashboardView.as_view(), name='dashboard'),
    # New path for the unacknowledged alerts list view
    path(
        'alerts/unacknowledged/',
        Tier1AlertListView.as_view(),
        name='tier1-unacknowledged-alerts'
    ),
    # API endpoint for auto-refresh (potentially for the main dashboard)
    path('api/alerts/', Tier1AlertDataAPIView.as_view(), name='api_alert_data'),
]
