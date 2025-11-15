from datetime import timedelta

from django import forms
from .models import AlertComment, SilenceRule
import json
from django.core.exceptions import ValidationError
from django.utils import timezone
import pytz
from pytz.exceptions import UnknownTimeZoneError

class AlertAcknowledgementForm(forms.Form):
    """
    Form for acknowledging alerts with a required comment.
    """
    comment = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        required=True,
        help_text="Please provide a comment for this acknowledgement."
    )


COMMON_TIMEZONES = pytz.common_timezones
TIMEZONE_CHOICES = [(tz, tz) for tz in COMMON_TIMEZONES]
TIMEZONE_SET = set(COMMON_TIMEZONES)


class ManualResolveForm(forms.Form):
    """Form used by managers to resolve an alert manually."""

    resolved_at = forms.DateTimeField(
        label='Resolution time',
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        input_formats=['%Y-%m-%dT%H:%M'],
        help_text='Select the date and time when the alert should be considered resolved.'
    )
    timezone = forms.ChoiceField(
        label='Timezone',
        choices=TIMEZONE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='The timezone for the provided resolution time.'
    )
    note = forms.CharField(
        label='Resolution note',
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        help_text='Optional context about why the alert was resolved manually.'
    )

    def __init__(self, *args, user_timezone='UTC', **kwargs):
        super().__init__(*args, **kwargs)
        timezone_choice = user_timezone if user_timezone in TIMEZONE_SET else 'UTC'
        self.fields['timezone'].initial = timezone_choice

        if not self.initial.get('resolved_at'):
            current_time = timezone.now()
            try:
                tz = pytz.timezone(timezone_choice)
                current_time = timezone.localtime(current_time, tz)
            except UnknownTimeZoneError:
                current_time = timezone.localtime(current_time)
            current_time = current_time.replace(second=0, microsecond=0)
            self.fields['resolved_at'].initial = current_time.strftime('%Y-%m-%dT%H:%M')

    def clean_timezone(self):
        tz_name = self.cleaned_data['timezone']
        if tz_name not in TIMEZONE_SET:
            raise ValidationError('Invalid timezone selection.')
        return tz_name

    def clean(self):
        cleaned_data = super().clean()
        resolved_at = cleaned_data.get('resolved_at')
        tz_name = cleaned_data.get('timezone')

        if not resolved_at or not tz_name:
            return cleaned_data

        try:
            tz = pytz.timezone(tz_name)
        except UnknownTimeZoneError:
            self.add_error('timezone', 'Invalid timezone selection.')
            return cleaned_data

        if timezone.is_aware(resolved_at):
            resolved_at = timezone.make_naive(resolved_at, timezone.get_current_timezone())

        localized_time = tz.localize(resolved_at)

        resolved_at_utc = localized_time.astimezone(timezone.utc)
        if resolved_at_utc > timezone.now() + timedelta(minutes=5):
            self.add_error('resolved_at', 'Resolution time cannot be in the future.')
            return cleaned_data

        cleaned_data['resolved_at'] = resolved_at_utc
        cleaned_data['resolved_at_local'] = localized_time
        return cleaned_data


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

