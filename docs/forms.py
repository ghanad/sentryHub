# docs/forms.py

from django import forms
from tinymce.widgets import TinyMCE
from .models import AlertDocumentation


class AlertDocumentationForm(forms.ModelForm):
    class Meta:
        model = AlertDocumentation
        fields = ['title', 'description']
        widgets = {
            'description': TinyMCE(
                attrs={'class': 'form-control'},
                mce_attrs={
                    'directionality': 'rtl',
                    'height': 400,
                    'width': '100%',
                    'plugins': '''
                        textcolor save link image media preview table contextmenu
                        fileupload table code lists fullscreen insertdatetime nonbreaking
                        contextmenu directionality searchreplace wordcount visualblocks
                        visualchars code fullscreen autolink lists charmap print hr
                        anchor pagebreak
                    ''',
                    'toolbar1': '''
                        fullscreen preview bold italic underline | fontselect,
                        fontsizeselect | forecolor backcolor | alignleft alignright |
                        aligncenter alignjustify | indent outdent | bullist numlist table |
                        | link image media | forecolor backcolor emoticons | |
                        ltr rtl | removeformat | help
                    ''',
                    'contextmenu': 'formats | link image',
                    'menubar': True,
                    'statusbar': True,
                }
            ),
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