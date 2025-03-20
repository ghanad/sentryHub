# docs/urls.py

from django.urls import path
from .views import (
    DocumentationListView,
    DocumentationDetailView,
    DocumentationCreateView,
    DocumentationUpdateView,
    DocumentationDeleteView,
    LinkDocumentationToAlertView,
    UnlinkDocumentationFromAlertView,
)

app_name = 'docs'

urlpatterns = [
    # Documentation CRUD
    path('', DocumentationListView.as_view(), name='documentation-list'),
    path('<int:pk>/', DocumentationDetailView.as_view(), name='documentation-detail'),
    path('new/', DocumentationCreateView.as_view(), name='documentation-create'),
    path('<int:pk>/edit/', DocumentationUpdateView.as_view(), name='documentation-update'),
    path('<int:pk>/delete/', DocumentationDeleteView.as_view(), name='documentation-delete'),
    
    # Alert linking
    path('link/<str:pk>/', LinkDocumentationToAlertView.as_view(), name='link-documentation'),
    path('unlink/<int:alert_group_id>/<int:documentation_id>/', 
         UnlinkDocumentationFromAlertView.as_view(), name='unlink-documentation'),
]