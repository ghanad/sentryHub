from django import forms
from .models import AlertComment, SilenceRule
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


class AlertDeleteForm(forms.Form):
    """Form used to confirm alert deletion by retyping the alert name."""

    confirmation = forms.CharField(
        label="Type the alert name to confirm deletion",
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text="Enter the alert name exactly to confirm you want to delete it.",
    )

    def __init__(self, *args, expected_value=None, **kwargs):
        self.expected_value = expected_value
        super().__init__(*args, **kwargs)
        if expected_value:
            self.fields['confirmation'].widget.attrs.setdefault('placeholder', expected_value)

    def clean_confirmation(self):
        value = self.cleaned_data.get('confirmation', '').strip()
        if not value:
            raise ValidationError("This field is required.")
        if self.expected_value and value != self.expected_value:
            raise ValidationError("The provided value does not match the alert name.")
        return value


class JSONTextareaWidget(forms.Textarea):
    """
    Custom Textarea widget for JSONField that handles None values during rendering.
    """
    def render(self, name, value, attrs=None, renderer=None):
        # Ensure value is a JSON string for rendering, even if it's None or a dict
        if value is None:
            value = '{}' # Render as empty JSON object string
        elif not isinstance(value, str):
             # If value is not None and not a string (e.g., a dict), dump it to JSON string
             value = json.dumps(value)
        # If value is already a string, use it directly

        return super().render(name, value, attrs, renderer)


class JSONDictField(forms.JSONField):
    """
    Custom JSONField that returns an empty dictionary for empty string input
    and handles None data during rendering.
    """
    def to_python(self, value):
        if value == '':
            return {} # Return empty dict for empty string
        if value is None:
            return {} # Also return empty dict for None
        return super().to_python(value)

    def bound_data(self, data, initial):
        """
        Return the value that should be used when the field is bound.
        Handles None data by returning an empty dictionary string representation.
        """
        if data is None:
            return '{}' # Return empty JSON string representation
        return super().bound_data(data, initial)


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

    # USE THE CUSTOM FIELD
    matchers = JSONDictField(
        widget=JSONTextareaWidget(attrs={
            'rows': 3,
            'class': 'form-control font-monospace',
            'placeholder': 'Enter labels as JSON, e.g., {"job": "node_exporter", "instance": "server1"}'
        }),
        initial={},
        required=True
    )

    class Meta:
        model = SilenceRule
        fields = ['matchers', 'starts_at', 'ends_at', 'comment']
        widgets = {
             'comment': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
             # DO NOT define 'matchers' widget here, it's set above
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
        if matchers_data is None: # Handle None case explicitly
             # If matchers is a required field in the model, this will be caught by the model validation.
             # However, adding a form-level validation provides a better user experience.
             raise ValidationError("This field is required.")
        elif isinstance(matchers_data, str): # If loaded from Textarea
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
             # This case might occur if the data is neither None, str, nor dict.
             # It's good to have a fallback validation.
             raise ValidationError("Invalid data format for matchers.")

    def clean(self):
        """
        Validate that ends_at is after starts_at.
        The handling of None matchers is now in JSONDictField's bound_data.
        """
        cleaned_data = super().clean()

        # Removed the explicit handling of cleaned_data['matchers'] = {} here
        # as it's now handled by the custom JSONDictField's bound_data method.

        starts_at = cleaned_data.get("starts_at")
        ends_at = cleaned_data.get("ends_at")

        if starts_at and ends_at:
            if ends_at <= starts_at:
                raise ValidationError("End time must be after start time.")
            # Optional: Check if ends_at is in the past? Depends on requirements.
            # if ends_at <= timezone.now():
            #     raise ValidationError("End time cannot be in the past.")

        return cleaned_data

