from django.views.generic import TemplateView, ListView, DetailView, FormView
from django.db.models import Count, Q
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.http import JsonResponse
from django.contrib import messages
from django.views.generic.detail import SingleObjectMixin
import logging
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views import View # Import basic View
from django.http import HttpResponse # Import HttpResponse

from .models import AlertGroup, AlertInstance, AlertComment, SilenceRule # Added SilenceRule
from .forms import AlertAcknowledgementForm, AlertCommentForm, SilenceRuleForm # Added SilenceRuleForm
from .services.alerts_processor import acknowledge_alert
from .services.silence_matcher import check_alert_silence # Import the function
from docs.services.documentation_matcher import match_documentation_to_alert

logger = logging.getLogger(__name__)


class AlertListView(LoginRequiredMixin, ListView):
    model = AlertGroup
    template_name = 'alerts/alert_list.html'
    context_object_name = 'alerts'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = AlertGroup.objects.all()
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(current_status=status)
        
        # Filter by severity
        severity = self.request.GET.get('severity')
        if severity:
            queryset = queryset.filter(severity=severity)
        
        # Filter by instance
        instance = self.request.GET.get('instance')
        if instance:
            queryset = queryset.filter(instance__icontains=instance)
        
        # Filter by acknowledgement status
        acknowledged = self.request.GET.get('acknowledged')
        if acknowledged == 'true':
            queryset = queryset.filter(acknowledged=True)
        elif acknowledged == 'false':
            queryset = queryset.filter(acknowledged=False)

        # Filter by silenced status
        silenced_filter = self.request.GET.get('silenced')
        if silenced_filter == 'yes':
            queryset = queryset.filter(is_silenced=True)
        elif silenced_filter == 'no':
            queryset = queryset.filter(is_silenced=False)
        # If '', show all (default)

        # Search by name or fingerprint
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(fingerprint__icontains=search) |
                Q(instance__icontains=search)
            )
        
        return queryset.order_by('-last_occurrence')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter parameters to context
        context['status'] = self.request.GET.get('status', '')
        context['severity'] = self.request.GET.get('severity', '')
        context['instance'] = self.request.GET.get('instance', '')
        context['acknowledged'] = self.request.GET.get('acknowledged', '')
        context['silenced_filter'] = self.request.GET.get('silenced', '') # Add silenced filter to context
        context['search'] = self.request.GET.get('search', '')

        # Calculate statistics counts for the filtered results
        alerts = context['alerts']
        context['firing_count'] = sum(1 for alert in alerts if alert.current_status == 'firing')
        context['critical_count'] = sum(1 for alert in alerts if alert.severity == 'critical')
        context['acknowledged_count'] = sum(1 for alert in alerts if alert.acknowledged)
        
        return context


class AlertDetailView(LoginRequiredMixin, DetailView):
    model = AlertGroup
    template_name = 'alerts/alert_detail.html'
    context_object_name = 'alert'
    slug_field = 'fingerprint'
    slug_url_kwarg = 'fingerprint'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        logger.info(f"Viewing alert details for alert: {self.object.name} (ID: {self.object.id})")
        
        # Get linked documentation for this alert
        context['linked_documentation'] = self.object.documentation_links.select_related('documentation').all()
        
        # Get alert instances for history with pagination
        page = self.request.GET.get('page', 1)
        try:
            page = int(page)
        except (TypeError, ValueError):
            page = 1
            
        instances = self.object.instances.all().order_by('-started_at')
        paginator = Paginator(instances, 10)  # Show 10 instances per page
        
        try:
            instances = paginator.page(page)
        except PageNotAnInteger:
            instances = paginator.page(1)
        except EmptyPage:
            instances = paginator.page(paginator.num_pages)
            
        context['instances'] = instances
        
        # Get acknowledgement history
        context['acknowledgement_history'] = self.object.acknowledgement_history.select_related(
            'acknowledged_by', 'alert_instance'
        ).order_by('-acknowledged_at')
        
        # Get comments
        comments_page = self.request.GET.get('comments_page', 1)
        try:
            comments_page = int(comments_page)
        except (TypeError, ValueError):
            comments_page = 1
            
        comments = self.object.comments.all().order_by('-created_at')
        comments_paginator = Paginator(comments, 10)  # 10 comments per page
        
        try:
            paginated_comments = comments_paginator.page(comments_page)
        except PageNotAnInteger:
            paginated_comments = comments_paginator.page(1)
        except EmptyPage:
            paginated_comments = comments_paginator.page(comments_paginator.num_pages)
            
        context['comments'] = paginated_comments
        
        # Add forms to context
        context['acknowledge_form'] = AlertAcknowledgementForm()
        context['comment_form'] = AlertCommentForm()
        
        # Add active tab to context
        context['active_tab'] = self.request.GET.get('tab', 'details')
        
        return context
    
    def post(self, request, *args, **kwargs):
        alert = self.get_object()
        logger.info(f"Processing POST request for alert: {alert.name} (ID: {alert.id})")
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        # Handle acknowledgement with required comment
        if 'acknowledge' in request.POST:
            form = AlertAcknowledgementForm(request.POST)
            if form.is_valid():
                comment_text = form.cleaned_data['comment']
                logger.info(f"Acknowledging alert: {alert.name} with comment: {comment_text}")
                
                # Create the comment first
                AlertComment.objects.create(
                    alert_group=alert,
                    user=request.user,
                    content=comment_text
                )
                
                # Then acknowledge the alert
                acknowledge_alert(alert, request.user, comment_text)
                
                if not is_ajax:
                    messages.success(request, "Alert has been acknowledged successfully.")
                return redirect('alerts:alert-detail', fingerprint=alert.fingerprint)
            else:
                logger.warning(f"Invalid acknowledgement form for alert: {alert.name}")
                if not is_ajax:
                    messages.error(request, "Please provide a comment when acknowledging an alert.")
                return self.get(request, *args, **kwargs)
        
        # Handle comment
        if 'comment' in request.POST:
            form = AlertCommentForm(request.POST)
            if form.is_valid():
                comment = form.save(commit=False)
                comment.alert_group = alert
                comment.user = request.user
                comment.save()
                logger.info(f"Added new comment to alert: {alert.name}")
                
                if is_ajax:
                    return JsonResponse({
                        'status': 'success',
                        'user': request.user.username,
                        'content': form.cleaned_data['content']
                    })
                else:
                    messages.success(request, "Comment added successfully.")
                    return redirect('alerts:alert-detail', fingerprint=alert.fingerprint)
            else:
                logger.warning(f"Invalid comment form for alert: {alert.name}")
                if is_ajax:
                    return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
                else:
                    messages.error(request, "Please provide a valid comment.")
                    return redirect('alerts:alert-detail', fingerprint=alert.fingerprint)
        
        return redirect('alerts:alert-detail', fingerprint=alert.fingerprint)


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('dashboard:dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'alerts/login.html', {'form': form})


# --- Silence Rule Views ---

class SilenceRuleListView(LoginRequiredMixin, ListView):
    model = SilenceRule
    template_name = 'alerts/silence_rule_list.html'
    context_object_name = 'silence_rules'
    paginate_by = 20

    def get_queryset(self):
        queryset = SilenceRule.objects.select_related('created_by').all()
        now = timezone.now()

        # Filter by status
        status_filter = self.request.GET.get('status', '')
        if status_filter == 'active':
            queryset = queryset.filter(starts_at__lte=now, ends_at__gt=now)
        elif status_filter == 'expired':
            queryset = queryset.filter(ends_at__lte=now)
        elif status_filter == 'scheduled':
            queryset = queryset.filter(starts_at__gt=now)

        # Search by comment or creator username
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(comment__icontains=search) |
                Q(created_by__username__icontains=search) |
                Q(matchers__icontains=search) # Basic JSON search (might be slow)
            )

        return queryset.order_by('-starts_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_filter'] = self.request.GET.get('status', '')
        context['search'] = self.request.GET.get('search', '')
        context['now'] = timezone.now() # Pass current time for template logic
        return context


class SilenceRuleCreateView(LoginRequiredMixin, CreateView):
    model = SilenceRule
    form_class = SilenceRuleForm
    template_name = 'alerts/silence_rule_form.html'
    success_url = reverse_lazy('alerts:silence-rule-list')

    def get_initial(self):
        """
        Provide initial data for the form, parsing labels from GET params.
        """
        initial = super().get_initial()
        initial_labels_json = self.request.GET.get('labels')
        if initial_labels_json:
            try:
                import json
                initial_labels = json.loads(initial_labels_json)
                if isinstance(initial_labels, dict):
                    # The form's clean_matchers expects a dict or a JSON string.
                    # Providing the dict directly as initial data is cleaner.
                    initial['matchers'] = initial_labels
                else:
                     logger.warning(f"Parsed labels JSON is not a dict: {initial_labels_json}")
                     messages.warning(self.request, "Could not pre-fill matchers: Invalid label format.")
            except json.JSONDecodeError:
                logger.warning(f"Could not decode initial labels JSON: {initial_labels_json}")
                messages.warning(self.request, "Could not pre-fill matchers: Invalid JSON.")
        return initial

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        # Call parent form_valid without showing default success message
        response = super().form_valid(form)
        
        # Get the newly created rule
        new_rule = self.object
        matchers = new_rule.matchers
        
        if matchers:
            try:
                logger.info(f"Finding alerts matching new silence rule ID {new_rule.id}")
                
                # Build query to find matching alerts
                filter_q = Q()
                for key, value in matchers.items():
                    filter_q &= Q(**{f'labels__{key}': value})
                
                matching_alerts = AlertGroup.objects.filter(filter_q)
                alert_count = matching_alerts.count()
                logger.info(f"Found {alert_count} alerts matching new silence rule ID {new_rule.id}")
                
                # Re-evaluate each matching alert
                for alert in matching_alerts:
                    check_alert_silence(alert)
                
                messages.success(
                    self.request,
                    f"Silence rule created successfully and {alert_count} matching alerts re-evaluated."
                )
            except Exception as e:
                logger.error(
                    f"Error re-evaluating alerts after creating silence rule ID {new_rule.id}: {str(e)}",
                    exc_info=True
                )
                messages.warning(
                    self.request,
                    "Silence rule was created, but an error occurred while re-evaluating matching alerts."
                )
        else:
            messages.success(
                self.request,
                "Silence rule created successfully."
            )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = "Create New Silence Rule"
        # Ensure matchers are displayed as pretty JSON if initial data was provided
        # The form widget now receives the dict from get_initial, but we want the textarea
        # to show the pretty-printed JSON string representation of that dict.
        if 'matchers' in self.get_initial(): # Check if initial data was successfully set
             initial_matchers_dict = self.get_initial()['matchers']
             if isinstance(initial_matchers_dict, dict):
                 import json
                 # Set the *value* for the widget rendering, not the field's initial
                 context['form'].fields['matchers'].widget.attrs['value'] = json.dumps(initial_matchers_dict, indent=2)

        return context


class SilenceRuleUpdateView(LoginRequiredMixin, UpdateView):
    model = SilenceRule
    form_class = SilenceRuleForm
    template_name = 'alerts/silence_rule_form.html'
    success_url = reverse_lazy('alerts:silence-rule-list')

    def form_valid(self, form):
        # Call parent form_valid without showing default success message
        response = super().form_valid(form)
        
        # Get the updated rule
        updated_rule = self.object
        matchers = updated_rule.matchers
        
        if matchers:
            try:
                logger.info(f"Finding alerts matching updated silence rule ID {updated_rule.id}")
                
                # Build query to find matching alerts
                filter_q = Q()
                for key, value in matchers.items():
                    filter_q &= Q(**{f'labels__{key}': value})
                
                matching_alerts = AlertGroup.objects.filter(filter_q)
                alert_count = matching_alerts.count()
                logger.info(f"Found {alert_count} alerts matching updated silence rule ID {updated_rule.id}")
                
                # Re-evaluate each matching alert
                for alert in matching_alerts:
                    check_alert_silence(alert)
                
                messages.success(
                    self.request,
                    f"Silence rule updated successfully and {alert_count} matching alerts re-evaluated."
                )
            except Exception as e:
                logger.error(
                    f"Error re-evaluating alerts after updating silence rule ID {updated_rule.id}: {str(e)}",
                    exc_info=True
                )
                messages.warning(
                    self.request,
                    "Silence rule was updated, but an error occurred while re-evaluating matching alerts."
                )
        else:
            messages.success(
                self.request,
                "Silence rule updated successfully."
            )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = "Edit Silence Rule"
        # Ensure matchers are displayed as pretty JSON when editing an existing rule
        # The form receives the model instance, and the 'matchers' field gets the dict.
        # We need to format it for the textarea widget.
        if self.object and isinstance(self.object.matchers, dict):
             import json
             # Set the *value* for the widget rendering
             context['form'].fields['matchers'].widget.attrs['value'] = json.dumps(self.object.matchers, indent=2)
        return context

    # Optional: Add permission check if needed
    # def get_object(self, queryset=None):
    #     obj = super().get_object(queryset)
    #     if obj.created_by != self.request.user and not self.request.user.is_staff:
    #         raise PermissionDenied("You do not have permission to edit this silence rule.")
    #     return obj


class SilenceRuleDeleteView(LoginRequiredMixin, DeleteView):
    model = SilenceRule
    template_name = 'alerts/silence_rule_confirm_delete.html'
    success_url = reverse_lazy('alerts:silence-rule-list')

    def form_valid(self, form):
        # Get the rule before deletion
        rule = self.get_object()
        rule_id = rule.id
        ends_at = rule.ends_at
        
        logger.info(f"User {self.request.user.username} deleting silence rule ID {rule_id}")
        
        # Find potentially affected alerts (silenced by this rule)
        affected_alerts = AlertGroup.objects.filter(
            is_silenced=True,
            silenced_until=ends_at
        ).values_list('id', flat=True)
        
        logger.info(f"Found {len(affected_alerts)} potentially affected alerts for rule ID {rule_id}")
        
        # Perform the actual deletion
        response = super().form_valid(form)
        
        # Re-check affected alerts if any were found
        if affected_alerts:
            try:
                alerts_to_recheck = AlertGroup.objects.filter(id__in=affected_alerts)
                for alert in alerts_to_recheck:
                    check_alert_silence(alert)
                
                messages.success(
                    self.request, 
                    f"Silence rule deleted successfully and {len(affected_alerts)} affected alerts re-evaluated."
                )
            except Exception as e:
                logger.error(
                    f"Error re-evaluating alerts after deleting silence rule ID {rule_id}: {str(e)}",
                    exc_info=True
                )
                messages.error(
                    self.request,
                    "Silence rule was deleted, but an error occurred while re-evaluating affected alerts."
                )
        else:
            messages.success(self.request, "Silence rule deleted successfully.")
            
        return response

    # Optional: Add permission check if needed
    # def get_object(self, queryset=None):
    #     obj = super().get_object(queryset)
    #     if obj.created_by != self.request.user and not self.request.user.is_staff:
    #         raise PermissionDenied("You do not have permission to delete this silence rule.")
    #     return obj
