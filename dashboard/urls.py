from django.urls import path
from .views import DashboardView, Tier1AlertListView, AdminDashboardView, AdminCommentsView, AdminAcknowledgementsView

app_name = 'dashboard'

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('main/', DashboardView.as_view(), name='main_dashboard_new'),
    path('tier1/', Tier1AlertListView.as_view(), name='tier1_dashboard_new'),
    path('admin-summary/', AdminDashboardView.as_view(), name='admin_dashboard_summary'),
    path('admin-comments/', AdminCommentsView.as_view(), name='admin_dashboard_comments'),
    path('admin-acks/', AdminAcknowledgementsView.as_view(), name='admin_dashboard_acks'),
]