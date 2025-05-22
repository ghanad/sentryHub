from django.views.generic import TemplateView, ListView, DetailView, FormView
from django.db.models import Count, Q, Min, OuterRef, Subquery, F, Value, Case, When, IntegerField, Max
from django.db.models.functions import Coalesce
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
from django.views import View
from django.http import HttpResponse, Http404, HttpResponseRedirect # Import Http404, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from .models import (
    AlertGroup, AlertInstance, AlertComment,
    SilenceRule
)
from .forms import (
    AlertAcknowledgementForm, AlertCommentForm,
    SilenceRuleForm
)
from .services.alerts_processor import acknowledge_alert
from .services.silence_matcher import check_alert_silence # Import the function
from docs.services.documentation_matcher import match_documentation_to_alert

logger = logging.getLogger(__name__)


class AlertListView(LoginRequiredMixin, ListView):
    model = AlertGroup
    template_name = 'alerts/alert_list.html'
    context_object_name = 'alerts'
    paginate_by = 10 # Changed from 20 to 10
    
    def get_queryset(self):
        # Subquery to get the first instance start time for each group (for sorting)
        first_instance_subquery = AlertInstance.objects.filter(
            alert_group=OuterRef('pk')
        ).order_by('started_at').values('started_at')[:1]

        # Subquery to get the minimum start time of active instances (for duration calculation)
        active_instances_subquery = AlertInstance.objects.filter(
            alert_group=OuterRef('pk'),
            status='firing'
        ).order_by('started_at').values('started_at')[:1]

        queryset = AlertGroup.objects.annotate(
            first_instance_start_time=Subquery(first_instance_subquery),
            current_problem_start_time=Coalesce(
                Subquery(active_instances_subquery),
                None
            ),
            latest_instance_start=Max('instances__started_at')
        )

        # --- Apply Filters ---
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(current_status=status)

        severity = self.request.GET.get('severity')
        if severity:
            queryset = queryset.filter(severity=severity)

        instance = self.request.GET.get('instance')
        if instance:
            queryset = queryset.filter(instance__icontains=instance)

        acknowledged = self.request.GET.get('acknowledged')
        if acknowledged == 'true':
            queryset = queryset.filter(acknowledged=True)
        elif acknowledged == 'false':
            queryset = queryset.filter(acknowledged=False)

        silenced_filter = self.request.GET.get('silenced')
        if silenced_filter == 'yes':
            queryset = queryset.filter(is_silenced=True)
        elif silenced_filter == 'no':
            queryset = queryset.filter(is_silenced=False)

        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(fingerprint__icontains=search) |
                Q(instance__icontains=search)
            )

        # --- Apply Source Filter ---
        source_filter_value = self.request.GET.get('source')
        if source_filter_value:
            queryset = queryset.filter(source=source_filter_value)
        # --- End Apply Source Filter ---
        # --- End Apply Filters ---

        # --- Ordering ---
        # Order all alerts by most recent instance start time (newest first)
        queryset = queryset.order_by(
             '-latest_instance_start', # Newest alerts first
             '-pk' # Secondary sort for alerts with same start time
         )

        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter parameters to context
        context['status'] = self.request.GET.get('status', '')
        context['severity'] = self.request.GET.get('severity', '')
        context['instance'] = self.request.GET.get('instance', '')
        context['acknowledged'] = self.request.GET.get('acknowledged', '')
        context['silenced_filter'] = self.request.GET.get('silenced', '') # Add silenced filter to context
        context['search'] = self.request.GET.get('search', '')
        
        # Add source filter parameter to context
        context['source_filter_value'] = self.request.GET.get('source', '')

        # Query for available sources for the filter dropdown
        context['available_sources'] = AlertGroup.objects.filter(source__isnull=False).values_list('source', flat=True).distinct().order_by('source')

        # Calculate statistics counts for the filtered results (before pagination)
        # Note: These counts reflect the total matching alerts, not just the current page.
        # If counts per page are needed, they should be calculated based on context['alerts'] or context['object_list']
        queryset = self.get_queryset() # Re-fetch the filtered queryset
        context['total_firing_count'] = queryset.filter(current_status='firing').count()
        context['total_critical_count'] = queryset.filter(severity='critical').count()
        context['total_acknowledged_count'] = queryset.filter(acknowledged=True).count()

        # Counts for the current page (if pagination is active)
        alerts_on_page = context.get('alerts') # Use the context object name
        if alerts_on_page:
             context['firing_count'] = sum(1 for alert in alerts_on_page if alert.current_status == 'firing')
             context['critical_count'] = sum(1 for alert in alerts_on_page if alert.severity == 'critical')
             context['acknowledged_count'] = sum(1 for alert in alerts_on_page if alert.acknowledged)
        else:
             context['firing_count'] = 0
             context['critical_count'] = 0
             context['acknowledged_count'] = 0


        return context

    def paginate_queryset(self, queryset, page_size):
         paginator = self.get_paginator(
             queryset,
             page_size,
             orphans=self.get_paginate_orphans(),
             allow_empty_first_page=self.get_allow_empty(),
         )
         page_kwarg = self.page_kwarg
         page = self.kwargs.get(page_kwarg) or self.request.GET.get(page_kwarg) or 1
         try:
             page_number = int(page)
         except ValueError:
             if page == "last":
                 page_number = paginator.num_pages
             else:
                 page_number = 1 # Default for non-integer

         try:
             page = paginator.page(page_number)
         except EmptyPage: # Catch page < 1 or page > num_pages
             if page_number < 1:
                  page = paginator.page(1) # Default to page 1 if page < 1
             else:
                  page = paginator.page(paginator.num_pages) # Default to last page if page > num_pages
         except PageNotAnInteger: # Should be caught by ValueError, but keep for safety
              page = paginator.page(1)

         return (paginator, page, page.object_list, page.has_other_pages())


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
            
        # Get all instances ordered by started_at (newest first)
        all_instances = self.object.instances.all().order_by('-started_at')
        
        # Paginate for the history tab
        paginator = Paginator(all_instances, 10)
        try:
            paginated_instances = paginator.page(page)
        except PageNotAnInteger:
            paginated_instances = paginator.page(1)
        except EmptyPage:
            paginated_instances = paginator.page(paginator.num_pages)
            
        # For the details tab, we want the first instance (most recent)
        context['instances'] = paginated_instances
        context['last_instance'] = all_instances.first() if all_instances.exists() else None
        
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
                
                # Determine redirect URL
                next_url = request.POST.get('next')
                if next_url:
                    # Validate next_url here if needed for security
                    redirect_url = next_url
                else:
                    redirect_url = reverse('alerts:alert-detail', kwargs={'fingerprint': alert.fingerprint})

                if not is_ajax:
                    messages.success(request, "Alert has been acknowledged successfully.")
                return redirect(redirect_url)
            else:
                logger.warning(f"Invalid acknowledgement form for alert: {alert.name}")
                if not is_ajax:
                    messages.error(request, "Please provide a comment when acknowledging an alert.")
                # Re-render the page with the invalid form
                # Manually build context needed for render_to_response
                context = {'alert': alert, 'acknowledge_form': form, 'comment_form': AlertCommentForm()}
                # Add other necessary context items if template requires them (e.g., history, instances)
                # For simplicity in fix, assuming template handles missing optional context
                return self.render_to_response(context)

        # Handle comment - Use 'content' which is the actual form field name
        if 'content' in request.POST:
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
                    # Redirect back to the detail page after adding a comment
                    messages.success(request, "Comment added successfully.")
                    # Comments don't usually need the 'next' parameter logic
                    return redirect('alerts:alert-detail', fingerprint=alert.fingerprint)
            else:
                logger.warning(f"Invalid comment form for alert: {alert.name}")
                if is_ajax:
                    return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
                else:
                    messages.error(request, "Please provide a valid comment.")
                    # Re-render the page with the invalid form
                    # Manually build context needed for render_to_response
                    context = {'alert': alert, 'comment_form': form, 'acknowledge_form': AlertAcknowledgementForm()}
                    # Add other necessary context items if template requires them
                    return self.render_to_response(context)

        # If neither acknowledge nor content was in POST, redirect (or handle as appropriate)
        logger.warning(f"POST request received for alert {alert.fingerprint} without 'acknowledge' or 'comment' data.")
        return redirect('alerts:alert-detail', fingerprint=alert.fingerprint)


@login_required
@require_POST # Ensure this view only accepts POST requests
def acknowledge_alert_from_list(request):
    """
    Handles acknowledging an alert directly from the list view modal.
    """
    fingerprint = request.POST.get('fingerprint')
    comment = request.POST.get('comment')

    if not fingerprint:
        messages.error(request, "Acknowledgement failed: Missing alert identifier.")
        return redirect('alerts:alert-list') # Redirect back to list

    if not comment:
        messages.error(request, "Acknowledgement failed: Comment is required.")
        # Ideally, redirect back with an error indicator for the specific modal,
        # but for simplicity, just redirect to the list for now.
        # Preserving query params is important here.
        redirect_url = reverse('alerts:alert-list')
        query_params = request.GET.urlencode() # Get original query params
        if query_params:
            redirect_url = f"{redirect_url}?{query_params}"
        return HttpResponseRedirect(redirect_url)

    alert = get_object_or_404(AlertGroup, fingerprint=fingerprint)

    if alert.acknowledged:
        messages.warning(request, f"Alert '{alert.name}' is already acknowledged.")
    else:
        try:
            # Use the existing service function which handles comment creation and status update
            acknowledge_alert(alert, request.user, comment)
            messages.success(request, f"Alert '{alert.name}' acknowledged successfully.")
            logger.info(f"Alert {fingerprint} acknowledged from list view by user {request.user.username}")
        except Exception as e:
            logger.error(f"Error acknowledging alert {fingerprint} from list view: {e}", exc_info=True)
            messages.error(request, "An error occurred while acknowledging the alert.")

    # Redirect back to the alert list, preserving original filters/page
    redirect_url = reverse('alerts:alert-list')
    query_params = request.GET.urlencode() # Get original query params from the page the modal was on
    if query_params:
        redirect_url = f"{redirect_url}?{query_params}"

    # Note: request.POST might contain pagination/filter params if the form included them,
    # but it's safer to reconstruct the URL from the previous page's GET params if possible.
    # A hidden input in the modal form capturing request.GET.urlencode() could be more robust.
    # For now, we assume the browser retains the GET params in the referer or the form action implicitly.

    return HttpResponseRedirect(redirect_url)


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
                return redirect('alerts:alert-list')
    else:
        form = AuthenticationForm()
    return render(request, 'alerts/login.html', {'form': form})


# --- Silence Rule Views ---

class SilenceRuleListView(LoginRequiredMixin, ListView):
    model = SilenceRule
    template_name = 'alerts/silence_rule_list.html'
    context_object_name = 'silence_rules'
    paginate_by = 20
    # allow_empty_first_page = True # Removed - didn't solve the 404

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

    def paginate_queryset(self, queryset, page_size):
        """Override to handle invalid page numbers gracefully and add logging."""
        paginator = self.get_paginator(
            queryset,
            page_size,
            orphans=self.get_paginate_orphans(),
            allow_empty_first_page=self.get_allow_empty(), # Use class attribute
        )
        page_kwarg = self.page_kwarg
        page = self.kwargs.get(page_kwarg) or self.request.GET.get(page_kwarg) or 1
        logger.debug(f"SilenceRuleListView: Requested page '{page}'")
        try:
            page_number = int(page)
        except ValueError:
            if page == "last":
                page_number = paginator.num_pages
            else:
                logger.warning(f"SilenceRuleListView: Invalid page number '{page}' requested. Defaulting to page 1.")
                page_number = 1

        try:
            page_obj = paginator.page(page_number)
            logger.debug(f"SilenceRuleListView: Returning page {page_obj.number} with {len(page_obj.object_list)} items.")
        except EmptyPage:
            # Django's default behavior for ListView with allow_empty_first_page=False
            # is to raise Http404 if the page number is invalid (> num_pages or < 1).
            # Let's mimic that default behavior more closely.
            if page_number < 1:
                 logger.warning(f"SilenceRuleListView: Invalid page number {page_number} requested. Defaulting to page 1.")
                 page_obj = paginator.page(1)
            else:
                 # Default to last page if page > num_pages, like AlertListView
                 logger.warning(f"SilenceRuleListView: Invalid page number {page_number} requested (max is {paginator.num_pages}). Defaulting to last page.")
                 page_obj = paginator.page(paginator.num_pages)
        except PageNotAnInteger: # Should be caught by ValueError, but keep for safety
             logger.warning(f"SilenceRuleListView: Non-integer page number '{page}' requested. Defaulting to page 1.")
             page_obj = paginator.page(1)

        return (paginator, page_obj, page_obj.object_list, page_obj.has_other_pages())


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
        if not matchers:
            messages.warning(self.request, "Silence rule created with no matchers. It will not match any alerts.")
        else:
            messages.success(self.request, "Silence rule created successfully.")
        
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Create New Silence Rule' # Add form title
        context['now'] = timezone.now()
        return context


class SilenceRuleUpdateView(LoginRequiredMixin, UpdateView):
    model = SilenceRule
    form_class = SilenceRuleForm
    template_name = 'alerts/silence_rule_form.html'
    success_url = reverse_lazy('alerts:silence-rule-list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Silence rule updated successfully.")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['now'] = timezone.now()
        context['is_update'] = True
        return context


class SilenceRuleDeleteView(LoginRequiredMixin, DeleteView):
    model = SilenceRule
    template_name = 'alerts/silence_rule_confirm_delete.html'
    success_url = reverse_lazy('alerts:silence-rule-list')

    def form_valid(self, form):
        rule = self.get_object()
        
        # Check if this rule is currently silencing any alerts
        affected_alerts = AlertGroup.objects.filter(
            silence_rule=rule,
            is_silenced=True
        ).count()
        
        response = super().form_valid(form)
        
        if affected_alerts > 0:
            messages.warning(
                self.request,
                f"Silence rule was deleted but was currently silencing {affected_alerts} alerts. "
                "Those alerts will remain silenced until their silence period expires."
            )
        else:
            messages.success(self.request, "Silence rule deleted successfully.")
        
        return response


# --- Jira Integration Rule Views ---



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
        context['is_update'] = True
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

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        rule = self.object
        rule_id = rule.id
        ends_at = rule.ends_at

        logger.info(f"User {request.user.username} deleting silence rule ID {rule_id}")

        # Find potentially affected alerts (silenced by this rule)
        # Use a range-based check for ends_at to account for potential microsecond differences
        affected_alerts_ids = AlertGroup.objects.filter(
            is_silenced=True,
            silenced_until=ends_at
        ).values_list('id', flat=True)
        
        # Store the list of IDs before deletion, as the queryset might become empty after deletion
        affected_alerts_list = list(affected_alerts_ids)
        initial_affected_count = len(affected_alerts_list)

        # Perform the actual deletion
        rule.delete()

        # Re-check affected alerts if any were found (use the stored list of IDs)
        if initial_affected_count > 0:
            try:
                alerts_to_recheck = AlertGroup.objects.filter(id__in=affected_alerts_list)
                for alert in alerts_to_recheck:
                    check_alert_silence(alert)
                
                messages.success(
                    request,
                    f"Silence rule deleted successfully and {initial_affected_count} affected alerts re-evaluated."
                )
            except Exception as e:
                logger.error(
                    f"Error re-evaluating alerts after deleting silence rule ID {rule_id}: {str(e)}",
                    exc_info=True
                )
                messages.error(
                    request,
                    "Silence rule was deleted, but an error occurred while re-evaluating affected alerts."
                )
        else:
            messages.success(request, "Silence rule deleted successfully.")
            
        return HttpResponseRedirect(self.get_success_url())

    # Optional: Add permission check if needed
    # def get_object(self, queryset=None):
    #     obj = super().get_object(queryset)
    #     if obj.created_by != self.request.user and not self.request.user.is_staff:
    #         raise PermissionDenied("You do not have permission to delete this silence rule.")
    #     return obj
