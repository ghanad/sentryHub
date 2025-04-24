from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='main'),
    path('tier1/', views.Tier1AlertListView.as_view(), name='tier1'),
    path('admin/', views.AdminDashboardView.as_view(), name='admin'),
]