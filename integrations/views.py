# integrations/views.py (Modified Code)
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404 # Added get_object_or_404
from django.db.models import Q # Import Q for search if needed
from django.shortcuts import render # Add render
from django.contrib.auth.decorators import login_required # Add login_required
from .services.jira_service import JiraService # Import the service

from integrations.models import JiraIntegrationRule
from integrations.forms import JiraIntegrationRuleForm
# Keep AlertGroup import only if needed for other parts of the view,
# otherwise it can be removed if solely used for the incorrect delete check.
from alerts.models import AlertGroup
import logging

logger = logging.getLogger(__name__)

class JiraRuleListView(LoginRequiredMixin, ListView):
    model = JiraIntegrationRule
    template_name = 'integrations/jira_rule_list.html'
    context_object_name = 'jira_rules'
    paginate_by = 20

    def get_queryset(self):
        # Keep existing queryset logic for filtering/searching
        queryset = JiraIntegrationRule.objects.all().order_by('-priority', 'name')

        active_filter = self.request.GET.get('active', '')
        if active_filter == 'true':
            queryset = queryset.filter(is_active=True)
        elif active_filter == 'false':
            queryset = queryset.filter(is_active=False)

        search = self.request.GET.get('search', '')
        if search:
            # Ensure Q is imported if using it
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        # Keep existing context data logic
        context = super().get_context_data(**kwargs)
        context['active_filter'] = self.request.GET.get('active', '')
        context['search'] = self.request.GET.get('search', '')
        return context


class JiraRuleCreateView(LoginRequiredMixin, CreateView):
    model = JiraIntegrationRule
    form_class = JiraIntegrationRuleForm
    template_name = 'integrations/jira_rule_form.html'
    success_url = reverse_lazy('integrations:jira-rule-list')

    def form_valid(self, form):
        messages.success(self.request, "Jira integration rule created successfully.")
        return super().form_valid(form)


class JiraRuleUpdateView(LoginRequiredMixin, UpdateView):
    model = JiraIntegrationRule
    form_class = JiraIntegrationRuleForm
    template_name = 'integrations/jira_rule_form.html'
    success_url = reverse_lazy('integrations:jira-rule-list')

    def form_valid(self, form):
        messages.success(self.request, "Jira integration rule updated successfully.")
        return super().form_valid(form)


class JiraRuleDeleteView(LoginRequiredMixin, DeleteView):
    model = JiraIntegrationRule
    template_name = 'integrations/jira_rule_confirm_delete.html'
    success_url = reverse_lazy('integrations:jira-rule-list')

    # Overriding delete() is often cleaner than form_valid for DeleteView
    # if you just need to add messages before deletion.
    def delete(self, request, *args, **kwargs):
        # Get the object before deleting it to use its details in the message
        self.object = self.get_object()
        rule_name = self.object.name
        logger.info(f"User {request.user.username} requested deletion of Jira rule '{rule_name}' (ID: {self.object.pk})")

        # Add the success message *before* calling the superclass delete
        # Using f-string for better readability
        messages.success(self.request, f"Jira integration rule '{rule_name}' deleted successfully.")

        # Call the standard delete method from the parent class (DeleteView)
        # This handles the actual deletion from the database.
        return super().delete(request, *args, **kwargs)

    # No need for form_valid override anymore as delete() handles the message.
    # No need for get_context_data as the incorrect check is removed.


@login_required
def jira_admin_view(request):
    """
    Admin view for Jira integration, including connection testing and test issue creation.
    """
    context = {
        'connection_tested': False,
        'connection_successful': False,
        'test_issue_created': False,
        'test_issue_key': None,
        'test_issue_error': False
    }
    if request.method == 'POST':
        if 'test_connection' in request.POST:
            jira_service = JiraService()
            is_connected = jira_service.check_connection()
            context['connection_tested'] = True
            context['connection_successful'] = is_connected
            if is_connected:
                messages.success(request, "Successfully connected to Jira.")
            else:
                messages.error(request, "Failed to connect to Jira. Check configuration and network.")
            # No redirect needed, just re-render the page with results
            return render(request, 'integrations/jira_admin.html', context)
        
        elif 'create_test_issue' in request.POST:
            from django.conf import settings
            try:
                test_project_key = settings.JIRA_CONFIG['test_project_key']
                test_issue_type = settings.JIRA_CONFIG['test_issue_type']
                
                jira_service = JiraService()
                issue_key = jira_service.create_issue(
                    project_key=test_project_key,
                    issue_type=test_issue_type,
                    summary="SentryHub Test Issue",
                    description="This is a test issue created automatically by SentryHub to verify Jira integration functionality."
                )
                
                if issue_key:
                    context['test_issue_created'] = True
                    context['test_issue_key'] = issue_key
                    messages.success(request, f"Successfully created test Jira issue: {issue_key}")
                else:
                    context['test_issue_created'] = True
                    context['test_issue_error'] = True
                    messages.error(request, "Failed to create test Jira issue. Check logs for details.")
            
            except KeyError as e:
                context['test_issue_created'] = True
                context['test_issue_error'] = True
                messages.error(request, f"Missing required JIRA_CONFIG setting: {e}")
            
            return render(request, 'integrations/jira_admin.html', context)

    # For GET request or initial page load
    return render(request, 'integrations/jira_admin.html', context)
