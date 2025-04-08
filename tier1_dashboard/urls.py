from django.urls import path, include
from .views import Tier1AlertListView # Removed Tier1AlertDetailView
from .api.views import Tier1AlertDataAPIView

app_name = 'tier1_dashboard'

urlpatterns = [
    path(
        'unacked/',
        Tier1AlertListView.as_view(),
        name='tier1-unacked-alerts'
    ),
    # Removed unused Tier 1 specific alert detail URL
    path('api/alerts/', Tier1AlertDataAPIView.as_view(), name='api_alert_data'),
]
