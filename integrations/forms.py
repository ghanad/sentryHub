from django import forms
import json
from django.core.exceptions import ValidationError
from django.conf import settings
from django.core.validators import validate_email
from .models import JiraIntegrationRule, SlackIntegrationRule, PhoneBook, SmsIntegrationRule

class JiraIntegrationRuleForm(forms.ModelForm):
    """
    Form for creating and editing JiraIntegrationRule objects.
    """
    def get_issue_types(self):
        """Get available Jira issue types from settings"""
        return settings.JIRA_CONFIG.get('ISSUE_TYPE_CHOICES', [])

    class Meta:
        model = JiraIntegrationRule
        fields = [
            'name', 'is_active', 'priority', # Removed 'description'
            'jira_project_key', 'jira_issue_type', 'assignee',
            'jira_title_template', 'jira_description_template', 'jira_update_comment_template',
            'match_criteria', 'watchers' # Added watchers
        ]
        widgets = {
            # Removed 'description' widget
            'jira_title_template': forms.Textarea(attrs={'rows': 2, 'class': 'form-control font-monospace'}),
            'jira_description_template': forms.Textarea(attrs={'rows': 5, 'class': 'form-control font-monospace'}),
            'jira_update_comment_template': forms.Textarea(attrs={'rows': 3, 'class': 'form-control font-monospace'}),
            'match_criteria': forms.Textarea(attrs={
                'rows': 5, # Increased rows for better visibility
                'class': 'form-control font-monospace',
                'placeholder': 'Enter JSON object, e.g. {"job": "node", "severity": "critical"}'
            }),
        }
        help_texts = {
            'jira_project_key': 'Jira project key where issues will be created (e.g. OPS)',
            'jira_issue_type': 'Type of Jira issue to create',
            'assignee': 'Jira username to assign the issue to (leave blank for no assignment)',
            'jira_title_template': 'Template for Jira issue title. Use {{ label_name }} or {{ annotation_name }}. Example: "Alert: {{ alertname }} on {{ instance }}"',
            'jira_description_template': 'Template for Jira issue description. Uses Django template syntax. Available context: labels, annotations, alertname, status, etc. See documentation for full context.',
            'jira_update_comment_template': 'Template for comment added when updating an issue (e.g., alert resolved/re-fired). Uses Django template syntax.',
            'match_criteria': 'JSON object defining label match criteria. E.g. {"job": "node", "severity": "critical"}',
            'watchers': 'Comma-separated list of Jira usernames to add as watchers (e.g., user1,user2,user3)', # Added help text for watchers
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Get single allowed project key from settings
        allowed_key = settings.JIRA_CONFIG.get('allowed_project_keys', [''])[0]
        
        # Set single value and make field read-only
        self.fields['jira_project_key'].initial = allowed_key
        self.fields['jira_project_key'].widget = forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly'
        })
        
        # Update issue_type to be a ChoiceField with available types
        self.fields['jira_issue_type'] = forms.ChoiceField(
            choices=self.get_issue_types(),
            widget=forms.Select(attrs={'class': 'form-control'}),
            help_text='Type of Jira issue to create'
        )
        
        # Set priority default
        self.fields['priority'].initial = 0

    def clean_match_criteria(self):
        """
        Validate that match_criteria is a valid JSON dictionary.
        """
        match_criteria = self.cleaned_data.get('match_criteria', '{}')

        if isinstance(match_criteria, dict):
            return match_criteria

        try:
            parsed = json.loads(match_criteria)
            if not isinstance(parsed, dict):
                raise ValidationError('Match criteria must be a valid JSON object (dictionary)')
            return parsed
        except json.JSONDecodeError:
            raise ValidationError('Invalid JSON format for match criteria')

    def clean(self):
        cleaned_data = super().clean()
        assignee = cleaned_data.get('assignee')
        if assignee and len(assignee) > 100:
            raise ValidationError('Assignee username must be less than 100 characters')
        return cleaned_data


class SlackIntegrationRuleForm(forms.ModelForm):
    """Form for creating and editing SlackIntegrationRule objects."""

    class Meta:
        model = SlackIntegrationRule
        fields = [
            'name', 'is_active', 'priority',
            'match_criteria', 'slack_channel', 'message_template', 'resolved_message_template',
        ]
        help_texts = {
            'slack_channel': "Leave empty to route via labels.channel or fallback default channel.",
            'match_criteria': "Optional. Leave empty to match all alerts (generic rule). Use labels__<key> for label matching.",
        }
        widgets = {
            'match_criteria': forms.Textarea(
                attrs={
                    'rows': 5,
                    'class': 'form-control font-monospace',
                    'placeholder': '{\n  "labels__severity": "critical",\n  "source": "prometheus"\n}'
                }
            ),
            'message_template': forms.Textarea(
                attrs={
                    'rows': 3,
                    'class': 'form-control font-monospace',
                    'placeholder': ':fire: [{{ alert_group.severity }}] {{ summary }}\nStarted: {{ latest_instance.started_at|format_datetime:user }}'
                }
            ),
            'resolved_message_template': forms.Textarea(
                attrs={
                    'rows': 3,
                    'class': 'form-control font-monospace',
                    'placeholder': ':white_check_mark: [{{ alert_group.severity }}] {{ summary }}\nStarted: {{ latest_instance.started_at|format_datetime:user }}\nEnded: {{ latest_instance.ended_at|format_datetime:user }}'
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make slack_channel optional at the form level (UI)
        if 'slack_channel' in self.fields:
            self.fields['slack_channel'].required = False
        # Allow creating a generic rule by leaving match_criteria empty
        if 'match_criteria' in self.fields:
            self.fields['match_criteria'].required = False
        # Set priority default
        if 'priority' in self.fields:
            self.fields['priority'].initial = 0

# Removed duplicate __init__; initialization handled above

    def clean_match_criteria(self):
        match_criteria = self.cleaned_data.get('match_criteria', '{}')

        if isinstance(match_criteria, dict):
            return match_criteria

        try:
            parsed = json.loads(match_criteria)
            if not isinstance(parsed, dict):
                raise ValidationError('Match criteria must be a valid JSON object (dictionary)')
            return parsed
        except json.JSONDecodeError:
            raise ValidationError('Invalid JSON format for match criteria')


class SlackTestMessageForm(forms.Form):
    """Simple form for sending test Slack messages."""
    channel = forms.CharField(
        label='Slack Channel',
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    message = forms.CharField(
        label='Message',
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'})
    )

class SlackTemplateTestForm(forms.Form):
    """
    Advanced template test form for Slack Admin page.
    Allows preview and sending of a Django-template-rendered message
    using a mock alert plus user-provided extra context.
    """
    channel = forms.CharField(
        label='Slack Channel',
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '#general'})
    )
    message_template = forms.CharField(
        label='Message Template',
        widget=forms.Textarea(attrs={
            'rows': 5,
            'class': 'form-control font-monospace',
            'placeholder': 'e.g. {{ summary }} started at {{ latest_instance.started_at|format_datetime:user }}'
        })
    )
    extra_context = forms.CharField(
        label='Extra Context (JSON)',
        required=False,
        help_text='Optional JSON to merge into mock alert_group. Structure: {"labels": {...}, "alert_group": {...}}',
        widget=forms.Textarea(attrs={
            'rows': 4,
            'class': 'form-control font-monospace',
            'placeholder': '{"labels": {"team": "ops"}, "alert_group": {"source": "prometheus"}}'
        })
    )

    def clean_extra_context(self):
        raw = self.cleaned_data.get('extra_context', '').strip()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise ValidationError('Extra context must be a JSON object')
            # Optional sanity sub-objects
            for key in ('labels', 'alert_group'):
                if key in parsed and not isinstance(parsed[key], dict):
                    raise ValidationError(f'Extra context "{key}" must be an object if provided')
            return parsed
        except json.JSONDecodeError:
            raise ValidationError('Invalid JSON format for extra context')


class PhoneBookForm(forms.ModelForm):
    class Meta:
        model = PhoneBook
        fields = ['name', 'phone_number']


class SmsIntegrationRuleForm(forms.ModelForm):
    class Meta:
        model = SmsIntegrationRule
        fields = [
            'name', 'is_active', 'priority',
            'match_criteria', 'recipients', 'use_sms_annotation',
            'firing_template', 'resolved_template',
        ]
        help_texts = {
            'recipients': 'Comma-separated list of names from PhoneBook.',
            'match_criteria': 'Optional JSON dict. Leave empty to match all alerts.',
        }
        widgets = {
            'match_criteria': forms.Textarea(attrs={'rows':5,'class':'form-control font-monospace'}),
            'firing_template': forms.Textarea(attrs={'rows':3,'class':'form-control font-monospace'}),
            'resolved_template': forms.Textarea(attrs={'rows':3,'class':'form-control font-monospace'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'match_criteria' in self.fields:
            self.fields['match_criteria'].required = False
        if 'recipients' in self.fields:
            self.fields['recipients'].required = False
        if 'priority' in self.fields:
            self.fields['priority'].initial = 0

    def clean_match_criteria(self):
        match_criteria = self.cleaned_data.get('match_criteria', '{}')
        if isinstance(match_criteria, dict):
            return match_criteria
        try:
            parsed = json.loads(match_criteria)
            if not isinstance(parsed, dict):
                raise ValidationError('Match criteria must be a valid JSON object (dictionary)')
            return parsed
        except json.JSONDecodeError:
            raise ValidationError('Invalid JSON format for match criteria')


class SmsTestForm(forms.Form):
    recipient = forms.ModelChoiceField(
        queryset=PhoneBook.objects.all(),
        label="Recipient",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    message = forms.CharField(
        label="Message",
        widget=forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
    )
