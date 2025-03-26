# alerts/urls.py

from django.urls import path, include
from .views import (
    AlertListView,
    AlertDetailView,
    login_view,  # این اگر استفاده نمی‌شود شاید بهتر باشد حذف شود
    SilenceRuleListView,
    SilenceRuleCreateView,
    SilenceRuleUpdateView,
    SilenceRuleDeleteView,
)

app_name = 'alerts'

urlpatterns = [
    path('silences/', SilenceRuleListView.as_view(), name='silence-rule-list'),
    path('silences/new/', SilenceRuleCreateView.as_view(), name='silence-rule-create'),
    path('silences/<int:pk>/edit/', SilenceRuleUpdateView.as_view(), name='silence-rule-update'),
    path('silences/<int:pk>/delete/', SilenceRuleDeleteView.as_view(), name='silence-rule-delete'),
    path('api/v1/', include('alerts.api.urls')),

    path('', AlertListView.as_view(), name='alert-list'),

    path('<str:fingerprint>/', AlertDetailView.as_view(), name='alert-detail'),
]