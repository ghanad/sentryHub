from django import forms
import json
from django.core.exceptions import ValidationError
from .models import JiraIntegrationRule

class JiraIntegrationRuleForm(forms.ModelForm):
    """
    Form for creating and editing JiraIntegrationRule objects.
    """
    class Meta:
        model = JiraIntegrationRule
        fields = ['name', 'description', 'is_active', 'priority',
                 'jira_project_key', 'jira_issue_type', 'match_criteria']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'match_criteria': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-control font-monospace',
                'placeholder': 'Enter JSON object, e.g. {"job": "node", "severity": "critical"}'
            }),
        }
        help_texts = {
            'jira_project_key': 'Jira project key where issues will be created (e.g. OPS)',
            'jira_issue_type': 'Type of Jira issue to create (e.g. Task, Bug)',
            'match_criteria': 'JSON object defining label match criteria. E.g. {"job": "node", "severity": "critical"}',
        }

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set priority default
        self.fields['priority'].initial = 0