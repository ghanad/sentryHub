from django.urls import path, include
from .views import (
    DashboardView,
    AlertListView,
    AlertDetailView,
    AlertHistoryView,
)

app_name = 'alerts'

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('alerts/', AlertListView.as_view(), name='alert-list'),
    path('alerts/<str:fingerprint>/', AlertDetailView.as_view(), name='alert-detail'),
    path('alerts/<str:fingerprint>/history/', AlertHistoryView.as_view(), name='alert-history'),
    path('api/v1/', include('alerts.api.urls')),
]