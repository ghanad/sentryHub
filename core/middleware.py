from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

class AdminAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # List of admin-related URL patterns
        admin_patterns = [
            '/admin-dashboard/',
            '/admin/',
            '/users/',
        ]

        # Check if the current path starts with any admin pattern
        is_admin_url = any(request.path.startswith(pattern) for pattern in admin_patterns)

        if is_admin_url:
            # If user is not authenticated or not staff, redirect to login
            if not request.user.is_authenticated or not request.user.is_staff:
                messages.error(request, 'You do not have permission to access this section.')
                return redirect(reverse('login'))

        response = self.get_response(request)
        return response 