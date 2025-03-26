# sentryHub/urls.py (updated)

"""
sentryHub URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views, logout
from django.views.generic.base import RedirectView
from django.shortcuts import redirect
from core.views import HomeView

def logout_view(request):
    logout(request)
    return redirect('login')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', logout_view, name='logout'),
    # Password change URLs with custom templates
    path('accounts/password_change/', auth_views.PasswordChangeView.as_view(
        template_name='registration/password_change.html'
    ), name='password_change'),
    path('accounts/password_change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='registration/password_change_done.html'
    ), name='password_change_done'),
    # Password reset URLs
    path('accounts/password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('accounts/password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('accounts/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('accounts/reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('', include('core.urls', namespace='core')),  # Include core URLs first
    path('alerts/', include('alerts.urls', namespace='alerts')),
    path('dashboard/', include('main_dashboard.urls', namespace='dashboard')),
    path('api/v1/', include('alerts.api.urls')), # Include the alerts API URLs
    path('api-auth/', include('rest_framework.urls')),
    path('docs/', include('docs.urls', namespace='docs')),
    path('tinymce/', include('tinymce.urls')),
    path('admin-dashboard/', include('admin_dashboard.urls', namespace='admin_dashboard')),
    path('tier1/', include('tier1_dashboard.urls', namespace='tier1_dashboard')), # Add this line
    path('users/', include('users.urls', namespace='users')),
]

# Change admin site header
admin.site.site_header = 'SentryHub Admin'
admin.site.site_title = 'SentryHub Admin Portal'
admin.site.index_title = 'Welcome to SentryHub Administration'
