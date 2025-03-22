from django import template
from django.utils import timezone
from datetime import timedelta

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
    return f'<span class="badge bg-{status_class}">{value}</span>' 