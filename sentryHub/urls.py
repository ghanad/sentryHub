"""
sentryHub URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.generic.base import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', include('alerts.urls', namespace='alerts')),
    path('api-auth/', include('rest_framework.urls')),
    path('docs/', include('docs.urls', namespace='docs')),
]

# Change admin site header
admin.site.site_header = 'SentryHub Admin'
admin.site.site_title = 'SentryHub Admin Portal'
admin.site.index_title = 'Welcome to SentryHub Administration'