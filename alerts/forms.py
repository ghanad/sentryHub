from django import forms
from .models import AlertComment, SilenceRule, JiraIntegrationRule, JiraRuleMatcher
import json
from django.core.exceptions import ValidationError
from django.utils import timezone

class AlertAcknowledgementForm(forms.Form):
    """
    Form for acknowledging alerts with a required comment.
    """
    comment = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        required=True,
        help_text="Please provide a comment for this acknowledgement."
    )


class AlertCommentForm(forms.ModelForm):
    """
    Form for adding comments to alerts.
    """
    class Meta:
        model = AlertComment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }


class SilenceRuleForm(forms.ModelForm):
    """
    Form for creating and editing SilenceRule objects.
    """
    # Use SplitDateTimeField for better UX
    starts_at = forms.SplitDateTimeField(
        widget=forms.SplitDateTimeWidget(
            date_attrs={'type': 'date', 'class': 'form-control me-2'},
            time_attrs={'type': 'time', 'class': 'form-control'}
        ),
        initial=timezone.now,
        required=True
    )
    ends_at = forms.SplitDateTimeField(
        widget=forms.SplitDateTimeWidget(
            date_attrs={'type': 'date', 'class': 'form-control me-2'},
            time_attrs={'type': 'time', 'class': 'form-control'}
        ),
        required=True
    )

    class Meta:
        model = SilenceRule
        fields = ['matchers', 'starts_at', 'ends_at', 'comment']
        widgets = {
            'matchers': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control font-monospace',
                'placeholder': 'Enter labels as JSON, e.g., {"job": "node_exporter", "instance": "server1"}'
            }),
            'comment': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
        help_texts = {
            'matchers': 'Enter the labels to match exactly in JSON format. All key-value pairs must match the alert\'s labels for the rule to apply.',
            'starts_at': 'The time the silence rule becomes active.',
            'ends_at': 'The time the silence rule expires.',
            'comment': 'Reason for creating this silence rule.',
        }

    def clean_matchers(self):
        """Validate that the matchers field contains valid JSON."""
        matchers_data = self.cleaned_data.get('matchers')
        if isinstance(matchers_data, str): # If loaded from Textarea
             try:
                 # Attempt to parse the JSON string
                 parsed_matchers = json.loads(matchers_data)
                 if not isinstance(parsed_matchers, dict):
                     raise ValidationError("Matchers must be a valid JSON object (e.g., {} or {\"key\": \"value\"}).")
                 # Optional: Add more validation, e.g., check for empty values if needed
                 return parsed_matchers # Return the parsed dict
             except json.JSONDecodeError:
                 raise ValidationError("Invalid JSON format for matchers.")
        elif isinstance(matchers_data, dict): # If already a dict (e.g., from initial data)
             return matchers_data
        else:
             raise ValidationError("Matchers must be provided as a JSON object.")

    def clean(self):
        """Validate that ends_at is after starts_at."""
        cleaned_data = super().clean()
        starts_at = cleaned_data.get("starts_at")
        ends_at = cleaned_data.get("ends_at")

        if starts_at and ends_at:
            if ends_at <= starts_at:
                raise ValidationError("End time must be after start time.")
            # Optional: Check if ends_at is in the past? Depends on requirements.
            # if ends_at <= timezone.now():
            #     raise ValidationError("End time cannot be in the past.")

        return cleaned_data


class JiraIntegrationRuleForm(forms.ModelForm):
    """
    Form for creating and editing JiraIntegrationRule objects.
    """
    class Meta:
        model = JiraIntegrationRule
        fields = ['name', 'description', 'is_active', 'priority',
                 'jira_project_key', 'jira_issue_type', 'matchers']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'matchers': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }
        help_texts = {
            'jira_project_key': 'Jira project key where issues will be created (e.g. OPS)',
            'jira_issue_type': 'Type of Jira issue to create (e.g. Task, Bug)',
            'matchers': 'Select one or more matchers. The rule applies if ALL selected matchers match the alert\'s labels.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Improve matchers selection with better queryset
        self.fields['matchers'].queryset = JiraRuleMatcher.objects.all().order_by('name')
        # Set priority default
        self.fields['priority'].initial = 0
