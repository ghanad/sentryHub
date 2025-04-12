from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AlertWebhookView, AlertGroupViewSet, AlertHistoryViewSet

router = DefaultRouter()
router.register(r'alerts', AlertGroupViewSet)
router.register(r'history', AlertHistoryViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('webhook/', AlertWebhookView.as_view(), name='alert-webhook'),
    path('docs/', include('documentations.api.urls')),
]