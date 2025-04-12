from django.urls import path

from .views import DashboardView
from documentations.api import views as docs_api_views

app_name = 'main_dashboard'
urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
]