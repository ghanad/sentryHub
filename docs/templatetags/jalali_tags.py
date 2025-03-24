from django import template
import jdatetime
from django.utils import timezone
import pytz

register = template.Library()

@register.filter(takes_context=True)
def to_jalali(value, date_format="%Y-%m-%d"):
    """Convert date to Jalali or keep as Gregorian based on user preference"""
    if not value:
        return value

    try:
        # Get user preference from context
        if hasattr(to_jalali, 'context'):
            context = to_jalali.context
            request = context.get('request')
            if request and hasattr(request, 'user') and request.user.is_authenticated:
                preference = request.user.profile.date_format_preference
            else:
                preference = 'gregorian'
        else:
            preference = 'gregorian'

        # If preference is gregorian, use normal date format
        if preference == 'gregorian':
            if isinstance(value, str):
                try:
                    value = timezone.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    try:
                        value = timezone.datetime.strptime(value, "%Y-%m-%d")
                    except ValueError:
                        return value
            return value.strftime(date_format)

        # Convert to datetime if string
        if isinstance(value, str):
            try:
                value = timezone.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    value = timezone.datetime.strptime(value, "%Y-%m-%d")
                except ValueError:
                    return value

        # Convert to Tehran timezone if datetime
        if isinstance(value, timezone.datetime):
            tehran_tz = pytz.timezone("Asia/Tehran")
            if timezone.is_aware(value):
                value = value.astimezone(tehran_tz)
            else:
                value = tehran_tz.localize(value)

        # Convert to Jalali
        if isinstance(value, timezone.datetime):
            return jdatetime.datetime.fromgregorian(datetime=value).strftime(date_format)
        elif hasattr(value, 'year'):
            return jdatetime.date.fromgregorian(date=value).strftime(date_format)
        
        return value
    except Exception as e:
        print(f"Error in to_jalali: {str(e)}")  # For debugging
        return value

@register.filter(takes_context=True)
def to_jalali_datetime(value, datetime_format="%Y-%m-%d %H:%M"):
    """Convert datetime to Jalali or keep as Gregorian based on user preference"""
    return to_jalali(value, datetime_format)

# Simple direct conversion filters without user preference
@register.filter
def force_jalali(value, date_format="%Y-%m-%d"):
    """Always convert date to Jalali format"""
    if not value:
        return value

    try:
        # Convert to datetime if string
        if isinstance(value, str):
            try:
                value = timezone.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    value = timezone.datetime.strptime(value, "%Y-%m-%d")
                except ValueError:
                    return value

        # Convert to Tehran timezone if datetime
        if isinstance(value, timezone.datetime):
            tehran_tz = pytz.timezone("Asia/Tehran")
            if timezone.is_aware(value):
                value = value.astimezone(tehran_tz)
            else:
                value = tehran_tz.localize(value)

        # Convert to Jalali
        if isinstance(value, timezone.datetime):
            return jdatetime.datetime.fromgregorian(datetime=value).strftime(date_format)
        elif hasattr(value, 'year'):
            return jdatetime.date.fromgregorian(date=value).strftime(date_format)
        
        return value
    except Exception as e:
        print(f"Error in force_jalali: {str(e)}")
        return value

@register.filter
def force_gregorian(value, date_format="%Y-%m-%d"):
    """Always keep date in Gregorian format"""
    if not value:
        return value

    try:
        if isinstance(value, str):
            try:
                value = timezone.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    value = timezone.datetime.strptime(value, "%Y-%m-%d")
                except ValueError:
                    return value
        return value.strftime(date_format)
    except Exception as e:
        print(f"Error in force_gregorian: {str(e)}")
        return value 