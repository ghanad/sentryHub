import json
from django import template
from django.utils import timezone
from datetime import timedelta
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
        # Check if user preference is available and set to Jalali
        if user and hasattr(user, 'profile') and user.profile.date_format_preference == 'jalali':
            # Attempt to use the force_jalali filter if available
            try:
                # Use absolute import based on app structure
                from core.templatetags.date_format_tags import force_jalali
                return force_jalali(value, format_string)
            except ImportError as e:
                 # Log the import error for debugging
                 import logging
                 logger = logging.getLogger(__name__)
                 logger.error(f"Could not import force_jalali from core.templatetags.date_format_tags: {e}")
                 # Fallback or log error if date_format_tags cannot be imported here
                 # For simplicity, falling back to Gregorian if import fails
                 return timezone.localtime(value).strftime(format_string)
        else:
            # Default to Gregorian or if preference is Gregorian
            return timezone.localtime(value).strftime(format_string)
    except Exception:
        # Graceful fallback in case of any error during formatting
        try:
            return value.strftime(format_string)
        except:
            return str(value) # Raw string representation as last resort
