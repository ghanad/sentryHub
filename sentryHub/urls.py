# sentryHub/urls.py (updated)

"""
sentryHub URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.generic.base import RedirectView
from core.views import HomeView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(
        template_name='registration/logged_out.html',
        next_page='/accounts/login/',
        http_method_names=['get', 'post']
    ), name='logout'),
    # Password reset URLs
    path('accounts/password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('accounts/password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('accounts/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('accounts/reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('', include('core.urls', namespace='core')),  # Include core URLs first
    path('alerts/', include('alerts.urls', namespace='alerts')),
    path('api-auth/', include('rest_framework.urls')),
    path('docs/', include('docs.urls', namespace='docs')),
    path('tinymce/', include('tinymce.urls')),
    path('admin-dashboard/', include('admin_dashboard.urls', namespace='admin_dashboard')),
    path('users/', include('users.urls', namespace='users')),
]

# Change admin site header
admin.site.site_header = 'SentryHub Admin'
admin.site.site_title = 'SentryHub Admin Portal'
admin.site.index_title = 'Welcome to SentryHub Administration'