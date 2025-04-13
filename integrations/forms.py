from django import forms
from integrations.models import JiraIntegrationRule, JiraRuleMatcher

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