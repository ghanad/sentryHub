from django.urls import path
from .views import (
    JiraRuleListView,
    JiraRuleCreateView,
    JiraRuleUpdateView,
    JiraRuleDeleteView,
    SlackRuleListView,
    SlackRuleCreateView,
    SlackRuleUpdateView,
    SlackRuleDeleteView,
    jira_admin_view,
    jira_rule_guide_view,
    slack_admin_view,
    slack_admin_guide_view,
    check_slack_template,
)

app_name = 'integrations'

urlpatterns = [
    path('jira-rules/', JiraRuleListView.as_view(), name='jira-rule-list'),
    path('jira-rules/new/', JiraRuleCreateView.as_view(), name='jira-rule-create'),
    path('jira-rules/<int:pk>/edit/', JiraRuleUpdateView.as_view(), name='jira-rule-update'),
    path('jira-rules/<int:pk>/delete/', JiraRuleDeleteView.as_view(), name='jira-rule-delete'),
    path('slack-rules/', SlackRuleListView.as_view(), name='slack-rule-list'),
    path('slack-rules/new/', SlackRuleCreateView.as_view(), name='slack-rule-create'),
    path('slack-rules/<int:pk>/edit/', SlackRuleUpdateView.as_view(), name='slack-rule-update'),
    path('slack-rules/<int:pk>/delete/', SlackRuleDeleteView.as_view(), name='slack-rule-delete'),
    path('jira/admin/', jira_admin_view, name='jira-admin'), # Add URL for the admin view
    path('slack/admin/', slack_admin_view, name='slack-admin'),
    path('jira-rules/guide/', jira_rule_guide_view, name='jira-rule-guide'),
    path('slack/admin/guide/', slack_admin_guide_view, name='slack-admin-guide'),
    path('slack-rules/check-template/', check_slack_template, name='slack-rule-check-template'),
]
