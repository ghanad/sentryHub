# Path: admin_dashboard/urls.py

from django.urls import path
from .views import AdminDashboardView, AdminCommentsView, AdminAcknowledgementsView

app_name = 'admin_dashboard'

urlpatterns = [
    path('', AdminDashboardView.as_view(), name='dashboard'),
    path('comments/', AdminCommentsView.as_view(), name='comments'),
    path('acknowledgements/', AdminAcknowledgementsView.as_view(), name='acknowledgements'),
]