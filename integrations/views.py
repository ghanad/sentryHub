# integrations/views.py (Modified Code)
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404  # Added get_object_or_404
from django.db.models import Q  # Import Q for search if needed
from django.shortcuts import render  # Add render
from django.contrib.auth.decorators import login_required  # Add login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils import timezone
from .services.jira_service import JiraService  # Import the service
from .services.slack_service import SlackService
from .services.sms_service import SmsService
from .exceptions import SmsNotificationError
import markdown
import re
import json

from integrations.models import (
    JiraIntegrationRule,
    SlackIntegrationRule,
    SmsIntegrationRule,
    SmsMessageLog,
    PhoneBook,
)
from integrations.forms import (
    JiraIntegrationRuleForm,
    SlackIntegrationRuleForm,
    SmsIntegrationRuleForm,
    PhoneBookForm,
    SmsTestForm,
)
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

        try:
            with open('documentations/JIRA_RULE.md', 'r', encoding='utf-8') as f:
                jira_rule_guide_content = f.read()
            context['jira_rule_guide_content'] = jira_rule_guide_content
        except FileNotFoundError:
            logger.error("Jira rule guide file not found.")
            context['jira_rule_guide_content'] = "Error loading guide: File not found."
        except Exception as e:
            logger.error(f"Error reading Jira rule guide file: {e}")
            context['jira_rule_guide_content'] = "Error loading guide."

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


class SlackRuleListView(LoginRequiredMixin, ListView):
    model = SlackIntegrationRule
    template_name = 'integrations/slack_rule_list.html'
    context_object_name = 'slack_rules'
    paginate_by = 20
    ordering = ['-priority', 'name']


class SlackRuleCreateView(LoginRequiredMixin, CreateView):
    model = SlackIntegrationRule
    form_class = SlackIntegrationRuleForm
    template_name = 'integrations/slack_rule_form.html'
    success_url = reverse_lazy('integrations:slack-rule-list')

    def form_valid(self, form):
        messages.success(self.request, "Slack integration rule created successfully.")
        return super().form_valid(form)


class SlackRuleUpdateView(LoginRequiredMixin, UpdateView):
    model = SlackIntegrationRule
    form_class = SlackIntegrationRuleForm
    template_name = 'integrations/slack_rule_form.html'
    success_url = reverse_lazy('integrations:slack-rule-list')

    def form_valid(self, form):
        messages.success(self.request, "Slack integration rule updated successfully.")
        return super().form_valid(form)


class SlackRuleDeleteView(LoginRequiredMixin, DeleteView):
    model = SlackIntegrationRule
    template_name = 'integrations/slack_rule_confirm_delete.html'
    success_url = reverse_lazy('integrations:slack-rule-list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        rule_name = self.object.name
        messages.success(self.request, f"Slack integration rule '{rule_name}' deleted successfully.")
        return super().delete(request, *args, **kwargs)



class PhoneBookListView(LoginRequiredMixin, ListView):
    model = PhoneBook
    template_name = 'integrations/phonebook_list.html'
    context_object_name = 'entries'
    paginate_by = 20

class PhoneBookCreateView(LoginRequiredMixin, CreateView):
    model = PhoneBook
    form_class = PhoneBookForm
    template_name = 'integrations/phonebook_form.html'
    success_url = reverse_lazy('integrations:phonebook-list')

class PhoneBookUpdateView(LoginRequiredMixin, UpdateView):
    model = PhoneBook
    form_class = PhoneBookForm
    template_name = 'integrations/phonebook_form.html'
    success_url = reverse_lazy('integrations:phonebook-list')

class PhoneBookDeleteView(LoginRequiredMixin, DeleteView):
    model = PhoneBook
    template_name = 'integrations/phonebook_confirm_delete.html'
    success_url = reverse_lazy('integrations:phonebook-list')

class SmsRuleListView(LoginRequiredMixin, ListView):
    model = SmsIntegrationRule
    template_name = 'integrations/sms_rule_list.html'
    context_object_name = 'sms_rules'
    paginate_by = 20
    ordering = ['-priority', 'name']

class SmsRuleCreateView(LoginRequiredMixin, CreateView):
    model = SmsIntegrationRule
    form_class = SmsIntegrationRuleForm
    template_name = 'integrations/sms_rule_form.html'
    success_url = reverse_lazy('integrations:sms-rule-list')

class SmsRuleUpdateView(LoginRequiredMixin, UpdateView):
    model = SmsIntegrationRule
    form_class = SmsIntegrationRuleForm
    template_name = 'integrations/sms_rule_form.html'
    success_url = reverse_lazy('integrations:sms-rule-list')

class SmsRuleDeleteView(LoginRequiredMixin, DeleteView):
    model = SmsIntegrationRule
    template_name = 'integrations/sms_rule_confirm_delete.html'
    success_url = reverse_lazy('integrations:sms-rule-list')


class SmsHistoryListView(LoginRequiredMixin, ListView):
    model = SmsMessageLog
    template_name = 'integrations/sms_history.html'
    context_object_name = 'sms_logs'
    paginate_by = 25

    def get_queryset(self):
        return (
            SmsMessageLog.objects.select_related('rule', 'alert_group')
            .order_by('-created_at')
        )

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
                    description="This is a test issue created automatically by SentryHub to verify Jira integration functionality.",
                    assignee=None  # No assignee for test issues
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


def _build_mock_alert_context():
    """
    Create a mock alert-like context similar to Slack/Jira templates.
    Core keys: labels, annotations, alertname, status, severity, instance, generator_url.
    Also includes a 'icons' helper map for convenient emojis in templates.
    """
    labels = {
        "job": "node_exporter",
        "instance": "server1:9100",
        "name": "server1",
        "severity": "critical",
        "alertname": "HighCPUUsage",
        "environment": "prod",
    }
    annotations = {
        "summary": "CPU usage is above 90% for the last 5 minutes.",
        "description": "Node exporter reports sustained high CPU utilization on server1.",
    }
    # Common emoji aliases for Slack (works as :emoji_name:)
    icons = {
        "fire": ":fire:",
        "check": ":white_check_mark:",
        "warning": ":warning:",
        "bell": ":bell:",
        "x": ":x:",
        "info": ":information_source:",
        "rocket": ":rocket:",
        "boom": ":boom:",
    }
    base = {
        "labels": labels,
        "annotations": annotations,
        "alertname": labels.get("alertname", "UnknownAlert"),
        "status": "firing",
        "severity": labels.get("severity", "warning"),
        "instance": labels.get("instance", ""),
        "generator_url": "http://prometheus.example.local/graph?g0.expr=cpu_usage",
        "icons": icons,
    }
    return base
 

def _build_mock_alert_group():
    """Create a mock AlertGroup for template previews."""
    labels = {
        "job": "node_exporter",
        "instance": "server1:9100",
        "name": "server1",
        "severity": "critical",
        "alertname": "HighCPUUsage",
        "environment": "prod",
    }
    annotations = {
        "summary": "CPU usage is above 90% for the last 5 minutes.",
        "description": "Node exporter reports sustained high CPU utilization on server1.",
    }
    ag = AlertGroup(
        fingerprint="demo-fingerprint",
        name=labels.get("alertname", "DemoAlert"),
        labels=labels,
        severity=labels.get("severity", "warning"),
        instance=labels.get("instance"),
        source="internet",
        current_status="firing",
        total_firing_count=2,
        acknowledged=False,
        acknowledged_by=None,
        acknowledgement_time=None,
        is_silenced=False,
        jira_issue_key="SNT-2020",
        last_occurrence=timezone.now(),
        first_occurrence=timezone.now(),
    )

    class _MockInstance:
        def __init__(self, annotations):
            self.annotations = annotations
            self.started_at = timezone.now()

    class _MockInstanceManager:
        def __init__(self, instance):
            self._instance = instance

        def order_by(self, *args, **kwargs):
            return self

        def first(self):
            return self._instance

    mock_instance = _MockInstance(annotations)
    ag.__dict__["instances"] = _MockInstanceManager(mock_instance)
    return ag


def _apply_extra_context(alert_group: AlertGroup, extra: dict) -> AlertGroup:
    """Merge user-provided values into the mock AlertGroup."""
    if not extra:
        return alert_group

    labels_extra = extra.get("labels") or {}
    if isinstance(labels_extra, dict):
        alert_group.labels.update(labels_extra)
        if "alertname" in labels_extra:
            alert_group.name = labels_extra["alertname"]
        if "instance" in labels_extra:
            alert_group.instance = labels_extra["instance"]
        if "severity" in labels_extra:
            alert_group.severity = labels_extra["severity"]

    ag_extra = extra.get("alert_group") or {}
    if isinstance(ag_extra, dict):
        for key, value in ag_extra.items():
            setattr(alert_group, key, value)

    return alert_group


@login_required
def slack_admin_view(request):
    """Admin page to send test messages and preview Slack templates."""
    from .forms import SlackTestMessageForm, SlackTemplateTestForm  # local import to avoid cycles
    service = SlackService()
    if request.method == "POST":
        if "send_simple" in request.POST:
            simple_form = SlackTestMessageForm(request.POST)
            template_form = SlackTemplateTestForm()  # empty for re-render
            if simple_form.is_valid():
                channel = simple_form.cleaned_data["channel"]
                message = simple_form.cleaned_data["message"]
                if service.send_notification(channel, message):
                    messages.success(request, "Slack message sent successfully.")
                else:
                    messages.error(request, "Failed to send Slack message.")
            return render(
                request,
                "integrations/slack_admin.html",
                {"form": simple_form, "template_form": template_form},
            )
        elif "preview_template" in request.POST or "send_template" in request.POST:
            simple_form = SlackTestMessageForm()
            template_form = SlackTemplateTestForm(request.POST)
            rendered_preview = None
            if template_form.is_valid():
                channel = template_form.cleaned_data["channel"]
                template_text = template_form.cleaned_data["message_template"]
                extra = template_form.cleaned_data.get("extra_context") or {}
                ag = _apply_extra_context(_build_mock_alert_group(), extra)
                from django.template import Template, Context
                try:
                    tmpl = Template(template_text)
                    rendered_preview = tmpl.render(Context({"alert_group": ag}))
                except Exception as exc:
                    messages.error(request, f"Template rendering failed: {exc}")
                    rendered_preview = None
                if rendered_preview and "send_template" in request.POST:
                    if service.send_notification(channel, rendered_preview):
                        messages.success(request, "Rendered template sent to Slack successfully.")
                    else:
                        messages.error(request, "Failed to send rendered template to Slack.")
            return render(
                request,
                "integrations/slack_admin.html",
                {
                    "form": simple_form,
                    "template_form": template_form,
                    "rendered_preview": rendered_preview,
                },
            )
    simple_form = SlackTestMessageForm()
    template_form = None
    try:
        from .forms import SlackTemplateTestForm as _TF
        template_form = _TF()
    except Exception:
        template_form = None
    return render(
        request,
        "integrations/slack_admin.html",
        {"form": simple_form, "template_form": template_form},
    )

@login_required
def slack_admin_guide_view(request):
    """
    View to display Slack Admin Template Testing guide rendered from Markdown to HTML.
    """
    content_html = "خطا در بارگذاری راهنما."
    try:
        with open('documentations/SLACK_ADMIN_GUIDE.md', 'r', encoding='utf-8') as f:
            guide_md = f.read()
        # Convert markdown to HTML (we already import markdown at top of file)
        content_html = markdown.markdown(
            guide_md,
            extensions=["extra", "codehilite", "sane_lists", "toc"]
        )
    except FileNotFoundError:
        logger.error("Slack admin guide file not found.")
        content_html = "Error loading guide: File not found."
    except Exception as e:
        logger.error(f"Error reading Slack admin guide file: {e}")
        content_html = "Error loading guide."

    context = {'guide_content_md': content_html}
    return render(request, 'integrations/slack_admin_guide.html', context)
@login_required
def sms_rule_guide_view(request):
    """
    View to display SMS Rule guide rendered from Markdown to HTML.
    """
    content_html = "خطا در بارگذاری راهنما."
    try:
        with open('documentations/SMS_RULE_GUIDE.md', 'r', encoding='utf-8') as f:
            guide_md = f.read()
        content_html = markdown.markdown(
            guide_md,
            extensions=["extra", "codehilite", "sane_lists", "toc"]
        )
    except FileNotFoundError:
        logger.error("SMS rule guide file not found.")
        content_html = "Error loading guide: File not found."
    except Exception as e:
        logger.error(f"Error reading SMS rule guide file: {e}")
        content_html = "Error loading guide."

    context = {'guide_content_md': content_html}
    return render(request, 'integrations/sms_rule_guide.html', context)

@login_required
def sms_admin_view(request):
    """Admin page for checking SMS balance and sending test messages."""
    service = SmsService()
    balance = None
    balance_error = None
    try:
        balance = service.get_balance()
    except Exception as exc:
        balance_error = str(exc)

    if request.method == "POST":
        form = SmsTestForm(request.POST)
        if form.is_valid():
            recipient = form.cleaned_data["recipient"]
            message = form.cleaned_data["message"]
            try:
                resp_data = service.send_sms(recipient.phone_number, message)
                if isinstance(resp_data, dict):
                    msg_status = (
                        resp_data.get("messages", [{}])[0].get("status")
                    )
                    status_msg = SmsService.STATUS_MESSAGES.get(
                        msg_status, "وضعیت نامشخص"
                    )
                    messages.info(
                        request,
                        f"Status {msg_status}: {status_msg}",
                    )
                else:
                    messages.error(request, "Failed to send SMS.")
            except SmsNotificationError:
                messages.error(request, "Network error sending SMS.")
            return redirect("integrations:sms-admin")
    else:
        form = SmsTestForm()

    return render(
        request,
        "integrations/sms_admin.html",
        {"form": form, "balance": balance, "balance_error": balance_error},
    )


@login_required
def jira_rule_guide_view(request):
    """
    View to display the raw Jira Integration Rules guide markdown content
    for client-side rendering.
    """
    guide_content_md = "Error loading guide."

    try:
        with open('documentations/JIRA_RULE.md', 'r', encoding='utf-8') as f:
            guide_content_md = f.read()
    except FileNotFoundError:
        logger.error("Jira rule guide file not found for guide view.")
        guide_content_md = "Error loading guide: File not found."
    except Exception as e:
        logger.error(f"Error reading Jira rule guide file: {e}")
        guide_content_md = "Error loading guide."

    context = {
        'guide_content_md': guide_content_md # Pass raw markdown content to the template
    }
    return render(request, 'integrations/jira_rule_guide.html', context)


# --- START: New View for Template Checking ---
@login_required
@require_POST
def check_slack_template(request):
    """
    An API endpoint to safely render and validate a Slack message template.
    Expects a JSON body with a 'template_string' key.
    """
    try:
        data = json.loads(request.body)
        template_string = data.get('template_string')

        if template_string is None:
            return JsonResponse({'status': 'error', 'error': 'Missing template_string.'}, status=400)

        # Build a mock alert group object for context, similar to the admin page
        mock_alert_group = _build_mock_alert_group()

        # --- Create a special context for rendering ---
        try:
            latest_instance = mock_alert_group.instances.order_by('-started_at').first()
        except Exception:
            latest_instance = None
        annotations = latest_instance.annotations if latest_instance else {}
        summary = annotations.get('summary', mock_alert_group.name)
        description = annotations.get('description', 'No description provided.')

        context = {
            'alert_group': mock_alert_group,
            'latest_instance': latest_instance,
            'annotations': annotations,
            'summary': summary,
            'description': description,
        }

        # Attempt to render the template
        try:
            from django.template import Template, Context, TemplateSyntaxError  # Local import
            template = Template(template_string)
            rendered_text = template.render(Context(context))
            return JsonResponse({'status': 'success', 'rendered': rendered_text.strip()})
        except TemplateSyntaxError as e:
            return JsonResponse({'status': 'error', 'error': f'Template Syntax Error: {e}'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'error': f'An unexpected error occurred: {e}'})

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'error': 'Invalid JSON body.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': f'Server error: {e}'}, status=500)
# --- END: New View ---


@login_required
@require_POST
def check_sms_template(request):
    """
    API endpoint to safely render and validate an SMS message template.
    Expects a JSON body with a 'template_string' key.
    """
    try:
        data = json.loads(request.body)
        template_string = data.get('template_string')

        if template_string is None:
            return JsonResponse({'status': 'error', 'error': 'Missing template_string.'}, status=400)

        mock_alert_group = _build_mock_alert_group()

        try:
            latest_instance = mock_alert_group.instances.order_by('-started_at').first()
        except Exception:
            latest_instance = None
        annotations = latest_instance.annotations if latest_instance else {}
        summary = annotations.get('summary', mock_alert_group.name)
        description = annotations.get('description', 'No description provided.')

        context = {
            'alert_group': mock_alert_group,
            'latest_instance': latest_instance,
            'annotations': annotations,
            'summary': summary,
            'description': description,
        }

        try:
            from django.template import Template, Context, TemplateSyntaxError  # Local import
            template = Template(template_string)
            rendered_text = template.render(Context(context))
            return JsonResponse({'status': 'success', 'rendered': rendered_text.strip()})
        except TemplateSyntaxError as e:
            return JsonResponse({'status': 'error', 'error': f'Template Syntax Error: {e}'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'error': f'An unexpected error occurred: {e}'})

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'error': 'Invalid JSON body.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': f'Server error: {e}'}, status=500)
