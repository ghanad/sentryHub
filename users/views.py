from django.shortcuts import render
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db import models, IntegrityError
from .forms import CustomUserCreationForm, CustomUserChangeForm

# Create your views here.

class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff

class UserListView(AdminRequiredMixin, ListView):
    model = User
    template_name = 'users/user_list.html'
    context_object_name = 'users'
    paginate_by = 20

    def get_queryset(self):
        queryset = User.objects.all().order_by('username')
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                models.Q(username__icontains=search_query) |
                models.Q(email__icontains=search_query) |
                models.Q(profile__department__icontains=search_query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        return context

class UserCreateView(AdminRequiredMixin, CreateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = 'users/user_form.html'
    success_url = reverse_lazy('users:user_list')

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success'})
            return response
        except IntegrityError as e:
            if 'auth_user.username' in str(e):
                if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'error',
                        'message': 'A user with this username already exists.',
                        'errors': {'username': ['This username is already taken.']}
                    })
                form.add_error('username', 'This username is already taken.')
                return self.form_invalid(form)
            raise

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            errors = {}
            for field, field_errors in form.errors.items():
                errors[field] = field_errors
            return JsonResponse({
                'status': 'error',
                'message': 'Please correct the errors below.',
                'errors': errors
            })
        return super().form_invalid(form)

class UserUpdateView(AdminRequiredMixin, UpdateView):
    model = User
    form_class = CustomUserChangeForm
    template_name = 'users/user_form.html'
    success_url = reverse_lazy('users:user_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success'})
        return response

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': 'Please correct the errors below.',
                'errors': form.errors
            })
        return super().form_invalid(form)

class UserDeleteView(AdminRequiredMixin, DeleteView):
    model = User
    template_name = 'users/user_confirm_delete.html'
    success_url = reverse_lazy('users:user_list')

    def get(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
            self.object.delete()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success'})
            return super().post(request, *args, **kwargs)
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
            raise

    def get_object(self):
        return get_object_or_404(User, pk=self.kwargs['pk'])
