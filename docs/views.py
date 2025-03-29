# docs/views.py

from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Q, Count
from django.contrib import messages
from django.http import JsonResponse

from .models import AlertDocumentation, DocumentationAlertGroup
from .forms import AlertDocumentationForm, DocumentationSearchForm
from alerts.models import AlertGroup


class DocumentationListView(LoginRequiredMixin, ListView):
    model = AlertDocumentation
    template_name = 'docs/documentation_list.html'
    context_object_name = 'documentations'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = AlertDocumentation.objects.all().annotate(
            linked_alerts_count=Count('alert_groups')
        )
        
        # Apply search filter
        query = self.request.GET.get('query', '').strip()
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | 
                Q(description__icontains=query)
            )
        
        # Default ordering by title
        return queryset.order_by('title')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add search form to context
        form = DocumentationSearchForm(self.request.GET or None)
        context['search_form'] = form
        
        # Add current filter params to context
        context['search_query'] = self.request.GET.get('query', '')
        
        return context


class DocumentationDetailView(LoginRequiredMixin, DetailView):
    model = AlertDocumentation
    template_name = 'docs/documentation_detail.html'
    context_object_name = 'documentation'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get linked alert groups
        linked_alerts = AlertGroup.objects.filter(
            documentation_links__documentation=self.object
        ).order_by('-last_occurrence')
        context['linked_alerts'] = linked_alerts
        
        return context


class DocumentationCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = AlertDocumentation
    form_class = AlertDocumentationForm
    template_name = 'docs/documentation_form.html'
    permission_required = 'docs.add_alertdocumentation'
    
    def get_success_url(self):
        return reverse('docs:documentation-detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Documentation created successfully.')
        return super().form_valid(form)


class DocumentationUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = AlertDocumentation
    form_class = AlertDocumentationForm
    template_name = 'docs/documentation_form.html'
    permission_required = 'docs.change_alertdocumentation'
    
    def get_success_url(self):
        return reverse('docs:documentation-detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Documentation updated successfully.')
        return super().form_valid(form)


class DocumentationDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = AlertDocumentation
    template_name = 'docs/documentation_confirm_delete.html'
    success_url = reverse_lazy('docs:documentation-list')
    permission_required = 'docs.delete_alertdocumentation'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Documentation deleted successfully.')
        return super().delete(request, *args, **kwargs)


class LinkDocumentationToAlertView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = AlertGroup
    template_name = 'docs/link_documentation.html'
    fields = []  # We don't need any fields from AlertGroup
    permission_required = 'alerts.change_alertgroup'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['documentations'] = AlertDocumentation.objects.all().order_by('title')
        context['current_docs'] = AlertDocumentation.objects.filter(
            alert_groups__alert_group=self.object
        )
        return context
    
    def post(self, request, *args, **kwargs):
        alert_group = self.get_object()
        documentation_id = request.POST.get('documentation_id')
        
        if documentation_id:
            documentation = get_object_or_404(AlertDocumentation, pk=documentation_id)
            
            # Check if already linked
            link, created = DocumentationAlertGroup.objects.get_or_create(
                documentation=documentation,
                alert_group=alert_group,
                defaults={'linked_by': request.user}
            )
            
            if created:
                messages.success(request, f'Alert linked to "{documentation.title}" documentation.')
            else:
                messages.info(request, f'Alert was already linked to this documentation.')
        
        return redirect('alerts:alert-detail', fingerprint=alert_group.fingerprint)


class UnlinkDocumentationFromAlertView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = DocumentationAlertGroup
    permission_required = 'alerts.change_alertgroup'
    
    def get_object(self):
        alert_group_id = self.kwargs.get('alert_group_id')
        documentation_id = self.kwargs.get('documentation_id')
        return get_object_or_404(
            DocumentationAlertGroup,
            alert_group_id=alert_group_id,
            documentation_id=documentation_id
        )
    
    def delete(self, request, *args, **kwargs):
        link = self.get_object()
        alert_fingerprint = link.alert_group.fingerprint
        documentation_title = link.documentation.title
        
        link.delete()
        messages.success(request, f'Alert unlinked from "{documentation_title}" documentation.')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success'})
        else:
            return redirect('alerts:alert-detail', fingerprint=alert_fingerprint)
    
    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)