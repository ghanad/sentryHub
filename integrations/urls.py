from django.urls import path
from .views import (
    JiraRuleListView,
    JiraRuleCreateView,
    JiraRuleUpdateView,
    JiraRuleDeleteView
)

app_name = 'integrations'

urlpatterns = [
    path('jira-rules/', JiraRuleListView.as_view(), name='jira-rule-list'),
    path('jira-rules/new/', JiraRuleCreateView.as_view(), name='jira-rule-create'),
    path('jira-rules/<int:pk>/edit/', JiraRuleUpdateView.as_view(), name='jira-rule-update'),
    path('jira-rules/<int:pk>/delete/', JiraRuleDeleteView.as_view(), name='jira-rule-delete'),
]