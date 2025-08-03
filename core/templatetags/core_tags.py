import json
import logging # Added import for logging
from django import template
from django.utils import timezone
from django.contrib.auth.models import Group
from datetime import timedelta, datetime
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def time_ago(value):
    """Convert a datetime to a human-readable time ago string."""
    if not value:
        return ""
    
    now = timezone.now()
    diff = now - value
    
    if diff < timedelta(minutes=1):
        return "just now"
    elif diff < timedelta(hours=1):
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif diff < timedelta(days=1):
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff < timedelta(days=30):
        days = diff.days
        return f"{days} day{'s' if days != 1 else ''} ago"
    else:
        months = diff.days // 30
        return f"{months} month{'s' if months != 1 else ''} ago"

@register.filter
def status_badge(value):
    """Convert a status string to a Bootstrap badge."""
    status_classes = {
        'active': 'success',
        'inactive': 'danger',
        'pending': 'warning',
        'unknown': 'secondary'
    }
    status_class = status_classes.get(value.lower(), 'secondary')
    # Use mark_safe for HTML output
    return mark_safe(f'<span class="badge bg-{status_class}">{value}</span>')

@register.filter(name='jsonify')
def jsonify(data):
    """
    Safely convert a Python variable (like a dict) into a JSON string.
    Useful for embedding data in HTML attributes.
    """
    if data is None:
        return 'null'
    try:
        # Use compact separators to save space in HTML attributes
        return json.dumps(data, separators=(',', ':'))
    except TypeError:
        # Handle non-serializable data gracefully if necessary
        return 'null' # Or return an empty object '{}' or empty string ''

@register.filter
def format_datetime(value, user=None, format_string="%Y-%m-%d %H:%M:%S"):
    """
    Formats a datetime object based on user preference (Jalali or Gregorian).
    Relies on date_format_tags being loaded elsewhere or assumes Gregorian if not.
    """
    if not value:
        return ""

    try:
        profile_pref = None
        if user:
            try:
                profile_pref = user.profile.date_format_preference
            except Exception:
                profile_pref = None

        if profile_pref == 'jalali':
            try:
                from core.templatetags.date_format_tags import force_jalali
                return force_jalali(value, format_string)
            except ImportError as e:
                logger = logging.getLogger(__name__)
                logger.error(
                    f"Could not import force_jalali from core.templatetags.date_format_tags: {e}"
                )
                return timezone.localtime(value).strftime(format_string)
        else:
            return timezone.localtime(value).strftime(format_string)
    except Exception:
        try:
            return value.strftime(format_string)
        except Exception:
            return str(value)  # Raw string representation as last resort

@register.filter
def has_group(user, group_name):
    """Check if user belongs to specified group"""
    if not user or not user.is_authenticated:
        return False
    if isinstance(group_name, Group):
        return group_name in user.groups.all()
    return user.groups.filter(name=group_name).exists()

@register.filter(name='add_class')
def add_class(field, css_classes):
    """Adds CSS classes to a form field's widget."""
    attrs = field.field.widget.attrs
    defined_classes = attrs.get('class', '')
    # Ensure spaces between existing and new classes
    if defined_classes:
        attrs['class'] = f'{defined_classes} {css_classes}'
    else:
        attrs['class'] = css_classes
    return field.as_widget(attrs=attrs)
@register.filter
def calculate_duration(start_time):
    """
    Calculates the duration between a start datetime and now.
    Returns a human-readable string like "3d 4h", "5h 12m", "3m", "<1m".
    """
    if not isinstance(start_time, (datetime)):
         return "-" # Return a placeholder if input is invalid

    # Ensure start_time is offset-aware for comparison with timezone.now()
    if timezone.is_naive(start_time):
         try:
            start_time = timezone.make_aware(start_time, timezone.get_default_timezone())
         except Exception:
             return "-" # Cannot make aware

    now = timezone.now()

    # Handle potential future start times gracefully
    if start_time > now:
         return "Starts soon"

    diff = now - start_time
    total_seconds = int(diff.total_seconds())

    if total_seconds < 0:
        return "Error"
    elif total_seconds < 60:
        return "<1m"
    elif total_seconds < 3600: # Less than 1 hour
        minutes = total_seconds // 60
        return f"{minutes}m"
    elif total_seconds < 86400: # Less than 1 day
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours}h {minutes}m"
    else: # 1 day or more
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        return f"{days}d {hours}h"
