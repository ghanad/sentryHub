from django.urls import path
from . import views as core_views

app_name = 'core'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('about/', core_views.AboutView.as_view(), name='about'),
] 