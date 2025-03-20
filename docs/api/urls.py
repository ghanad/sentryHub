# docs/api/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DocumentationViewSet, AlertDocumentationLinkViewSet

router = DefaultRouter()
router.register(r'docs', DocumentationViewSet)
router.register(r'links', AlertDocumentationLinkViewSet)

urlpatterns = [
    path('', include(router.urls)),
]