from django.urls import path, include
from .views import Tier1AlertListView

app_name = 'tier1_dashboard'

urlpatterns = [
    path(
        'unacked/',
        Tier1AlertListView.as_view(),
        name='tier1-unacked-alerts'
    ),
]
