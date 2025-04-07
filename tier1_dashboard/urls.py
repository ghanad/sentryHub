from django.urls import path, include
from .views import Tier1AlertListView, Tier1AlertDetailView
from .api.views import Tier1AlertDataAPIView

app_name = 'tier1_dashboard'

urlpatterns = [
    path(
        'unacked/',
        Tier1AlertListView.as_view(),
        name='tier1-unacked-alerts'
    ),
    path(
        'alerts/<str:fingerprint>/',
        Tier1AlertDetailView.as_view(),
        name='tier1-alert-detail'
    ),
    path('api/alerts/', Tier1AlertDataAPIView.as_view(), name='api_alert_data'),
]
