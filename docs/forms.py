# docs/forms.py

from django import forms
from .models import AlertDocumentation


class AlertDocumentationForm(forms.ModelForm):
    class Meta:
        model = AlertDocumentation
        fields = ['title', 'description']
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 5, 
                'class': 'form-control', 
                'dir': 'rtl'
            }),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
        }
        help_texts = {
            'title': 'Enter the exact alert name (alertname) for automatic matching.',
        }


class DocumentationSearchForm(forms.Form):
    search = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search documentation...'
        })
    )