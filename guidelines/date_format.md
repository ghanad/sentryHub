# Date Formatting in SentryHub

## Overview
SentryHub supports both Gregorian (Western) and Jalali (Persian) date formats. Users can choose their preferred date format in their profile settings. This document explains how to implement date formatting in templates.

## Template Tags

### Loading the Template Tags
```html
{% load date_format_tags %}
```

### Available Filters

#### 1. force_jalali
Always converts a date to Jalali format, regardless of user preference.

```html
{{ date_value|force_jalali }}  <!-- Default format: YYYY-MM-DD -->
{{ date_value|force_jalali:"%Y-%m-%d %H:%M:%S" }}  <!-- With custom format -->
```

#### 2. force_gregorian
Always keeps a date in Gregorian format, regardless of user preference.

```html
{{ date_value|force_gregorian }}  <!-- Default format: YYYY-MM-DD -->
{{ date_value|force_gregorian:"%Y-%m-%d %H:%M:%S" }}  <!-- With custom format -->
```

### User Preference-Based Formatting
To respect user's date format preference:

```html
{% if user.profile.date_format_preference == 'jalali' %}
    {{ date_value|force_jalali:"%Y-%m-%d %H:%M:%S" }}
{% else %}
    {{ date_value|force_gregorian:"%Y-%m-%d %H:%M:%S" }}
{% endif %}
```

## Date Format Strings

### Common Format Patterns
- `%Y`: Year (4 digits)
- `%m`: Month (01-12)
- `%d`: Day (01-31)
- `%H`: Hour (00-23)
- `%M`: Minute (00-59)
- `%S`: Second (00-59)

### Examples
```html
<!-- Date only -->
{{ date_value|force_jalali:"%Y-%m-%d" }}

<!-- Date and time -->
{{ date_value|force_jalali:"%Y-%m-%d %H:%M:%S" }}

<!-- Custom format -->
{{ date_value|force_jalali:"%Y/%m/%d" }}
```

## Implementation Examples

### In Documentation Detail Template
```html
<tr>
    <th>Created At</th>
    <td>
        {% if user.profile.date_format_preference == 'jalali' %}
            {{ documentation.created_at|force_jalali:"%Y-%m-%d %H:%M:%S" }}
        {% else %}
            {{ documentation.created_at|force_gregorian:"%Y-%m-%d %H:%M:%S" }}
        {% endif %}
    </td>
</tr>
```

### In User Profile Template
```html
<tr>
    <th>Date Joined</th>
    <td>
        {% if user.profile.date_format_preference == 'jalali' %}
            {{ user.date_joined|force_jalali:"%Y-%m-%d %H:%M:%S" }}
        {% else %}
            {{ user.date_joined|force_gregorian:"%Y-%m-%d %H:%M:%S" }}
        {% endif %}
    </td>
</tr>
```

## Technical Details

### Location
The template tags are located in:
```
core/templatetags/date_format_tags.py
```

### Dependencies
- `jdatetime`: For Jalali date conversion
- `pytz`: For timezone handling
- Django's timezone utilities

### Error Handling
The template tags include built-in error handling:
- Returns original value if conversion fails
- Handles null/empty values gracefully
- Supports both datetime and date objects
- Handles string date inputs

## Best Practices

1. **Consistency**: Use the same date format pattern throughout your templates
2. **Default Format**: Use `YYYY-MM-DD` as the default date format
3. **Timezone Awareness**: All datetime values are converted to Tehran timezone for Jalali dates
4. **User Preference**: Always respect user's date format preference unless there's a specific reason not to
5. **Error Handling**: No need to add extra error checking in templates; the filters handle errors gracefully

## Common Issues and Solutions

### Issue: Dates Not Converting
Check that:
- Template tags are properly loaded
- Date value is a valid datetime/date object or string
- Format string matches the date value type

### Issue: Wrong Timezone
- Jalali dates are automatically converted to Tehran timezone
- Ensure your datetime objects are timezone-aware

### Issue: Format Not Applied
- Verify the format string syntax
- Check that the value is not None
- Ensure the date string matches expected input format

## Future Improvements
- Add support for more date format patterns
- Consider adding localized month names
- Add support for relative dates ("2 days ago", etc.) 