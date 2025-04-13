# alerts/urls.py

from django.urls import path, include
from .views import (
    AlertListView,
    AlertDetailView,
    SilenceRuleListView,
    SilenceRuleCreateView,
    SilenceRuleUpdateView,
    SilenceRuleDeleteView,
    acknowledge_alert_from_list,
    JiraRuleListView,
    JiraRuleCreateView,
    JiraRuleUpdateView,
    JiraRuleDeleteView,
)

app_name = 'alerts'

urlpatterns = [
    path('silences/', SilenceRuleListView.as_view(), name='silence-rule-list'),
    path('silences/new/', SilenceRuleCreateView.as_view(), name='silence-rule-create'),
    path('silences/<int:pk>/edit/', SilenceRuleUpdateView.as_view(), name='silence-rule-update'),
    path('silences/<int:pk>/delete/', SilenceRuleDeleteView.as_view(), name='silence-rule-delete'),
    
    path('jira-rules/', JiraRuleListView.as_view(), name='jira-rule-list'),
    path('jira-rules/new/', JiraRuleCreateView.as_view(), name='jira-rule-create'),
    path('jira-rules/<int:pk>/edit/', JiraRuleUpdateView.as_view(), name='jira-rule-update'),
    path('jira-rules/<int:pk>/delete/', JiraRuleDeleteView.as_view(), name='jira-rule-delete'),
    
    path('api/v1/', include('alerts.api.urls')),

    path('', AlertListView.as_view(), name='alert-list'),
    path('acknowledge/', acknowledge_alert_from_list, name='acknowledge-alert-from-list'), # Moved before fingerprint
    path('<str:fingerprint>/', AlertDetailView.as_view(), name='alert-detail'),
]