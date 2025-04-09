# alerts/urls.py

from django.urls import path, include
from .views import (
    AlertListView,
    AlertDetailView,
    SilenceRuleListView,
    SilenceRuleCreateView,
    SilenceRuleUpdateView,
    SilenceRuleDeleteView,
    acknowledge_alert_from_list, # Import the new view
)

app_name = 'alerts'

urlpatterns = [
    path('silences/', SilenceRuleListView.as_view(), name='silence-rule-list'),
    path('silences/new/', SilenceRuleCreateView.as_view(), name='silence-rule-create'),
    path('silences/<int:pk>/edit/', SilenceRuleUpdateView.as_view(), name='silence-rule-update'),
    path('silences/<int:pk>/delete/', SilenceRuleDeleteView.as_view(), name='silence-rule-delete'),
    path('api/v1/', include('alerts.api.urls')),

    path('', AlertListView.as_view(), name='alert-list'),
    path('acknowledge/', acknowledge_alert_from_list, name='acknowledge-alert-from-list'), # Moved before fingerprint
    path('<str:fingerprint>/', AlertDetailView.as_view(), name='alert-detail'),
]