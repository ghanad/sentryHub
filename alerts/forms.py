from django import forms
from .models import AlertComment

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