from django.urls import path, include
from core.views import DashboardView
from .views import (
    AlertListView,
    AlertDetailView,
    login_view,
)

app_name = 'alerts'

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('alerts/', AlertListView.as_view(), name='alert-list'),
    path('alerts/<str:fingerprint>/', AlertDetailView.as_view(), name='alert-detail'),
    path('login/', login_view, name='login'),
    path('api/v1/', include('alerts.api.urls')),
]