from django.urls import path
from .views import DashboardView, Tier1AlertListView, AdminDashboardView, AdminCommentsView, AdminAcknowledgementsView
from .views import tier1_alerts_sse_stream

app_name = 'dashboard'

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('main/', DashboardView.as_view(), name='main_dashboard_new'),
    path('tier1/', Tier1AlertListView.as_view(), name='tier1_dashboard_new'),
    # SSE stream for Tier1 latest alerts (limit=20)
    path('api/tier1/stream', tier1_alerts_sse_stream, name='tier1_sse_stream'),
    path('admin-summary/', AdminDashboardView.as_view(), name='admin_dashboard_summary'),
    path('admin-comments/', AdminCommentsView.as_view(), name='admin_dashboard_comments'),
    path('admin-acks/', AdminAcknowledgementsView.as_view(), name='admin_dashboard_acks'),
]