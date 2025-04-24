from django.urls import path
from .views import DashboardView

app_name = 'dashboard'

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('main/', DashboardView.as_view(), name='main_dashboard_new'),
]