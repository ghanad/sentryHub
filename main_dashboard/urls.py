from django.urls import path, include

app_name = 'dashboard'

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
]