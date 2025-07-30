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
    MacroListView,
    MacroCreateView,
    MacroUpdateView,
    MacroDeleteView,
    macro_guide_view,
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
    path('link/<str:pk>/', LinkDocumentationToAlertView.as_view(), name='link-documentation-to-alert'),  # Backward compatibility
    path('unlink/<int:alert_group_id>/<int:documentation_id>/',
         UnlinkDocumentationFromAlertView.as_view(), name='unlink-documentation'),

    # Macros
    path('macros/', MacroListView.as_view(), name='macro-list'),
    path('macros/new/', MacroCreateView.as_view(), name='macro-create'),
    path('macros/<int:pk>/edit/', MacroUpdateView.as_view(), name='macro-update'),
    path('macros/<int:pk>/delete/', MacroDeleteView.as_view(), name='macro-delete'),
    path('macros/guide/', macro_guide_view, name='macro-guide'),
]