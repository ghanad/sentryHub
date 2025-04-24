from django.urls import path
from .views import DashboardView, Tier1AlertListView

app_name = 'dashboard'

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('main/', DashboardView.as_view(), name='main_dashboard_new'),
    path('tier1/', Tier1AlertListView.as_view(), name='tier1_dashboard_new'),
]