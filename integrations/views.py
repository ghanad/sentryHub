from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect

from integrations.models import JiraIntegrationRule
from integrations.forms import JiraIntegrationRuleForm
import logging

logger = logging.getLogger(__name__)

class JiraRuleListView(LoginRequiredMixin, ListView):
    model = JiraIntegrationRule
    template_name = 'integrations/jira_rule_list.html'
    context_object_name = 'jira_rules'
    paginate_by = 20

    def get_queryset(self):
        queryset = JiraIntegrationRule.objects.all().order_by('-priority', 'name')
        
        # Filter by active status
        active_filter = self.request.GET.get('active', '')
        if active_filter == 'true':
            queryset = queryset.filter(is_active=True)
        elif active_filter == 'false':
            queryset = queryset.filter(is_active=False)
            
        # Search by name or description
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
            
        return queryset

    def get_context_data(self, **kwargs):
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

    def form_valid(self, form):
        rule = self.get_object()
        
        # Check if this rule is referenced by any alerts
        affected_alerts = AlertGroup.objects.filter(
            jira_issue_key__isnull=False
        ).count()
        
        if affected_alerts > 0:
            messages.warning(
                self.request,
                f"Cannot delete rule '{rule.name}' - it's referenced by {affected_alerts} alerts."
            )
            return redirect('integrations:jira-rule-list')
            
        messages.success(self.request, "Jira integration rule deleted successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['affected_alerts'] = AlertGroup.objects.filter(
            jira_issue_key__isnull=False
        ).count()
        return context
