# Notification System Guidelines

## Overview
The project uses a unified notification system built as a wrapper around Toastr.js with added functionality and consistent styling.

## Basic Usage
```javascript
// Display a success message
SentryNotification.success('Operation completed successfully');

// Display an error message
SentryNotification.error('An error occurred');

// Display a warning
SentryNotification.warning('Please be careful');

// Display an information message
SentryNotification.info('Important information');
```

## Advanced Options
All methods accept an optional settings object:

```javascript
SentryNotification.success('Success message', {
    timeOut: 5000,              // Display duration in milliseconds
    closeButton: true,          // Show close button
    progressBar: true,          // Show progress bar
    positionClass: "toast-top-right", // Position on screen
    preventDuplicates: true,    // Prevent duplicate notifications
    clearBeforeShow: true       // Clear existing notifications
});
```

## AJAX Example
```javascript
fetch('/api/endpoint/', {
    method: 'POST',
    body: formData,
    headers: {
        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
        'X-Requested-With': 'XMLHttpRequest'
    }
})
.then(response => response.json())
.then(data => {
    if (data.status === 'success') {
        SentryNotification.success('Operation successful');
    } else {
        SentryNotification.error(data.message || 'An error occurred');
    }
})
.catch(error => {
    console.error('Error:', error);
    SentryNotification.error('Server communication error');
});
```

## Clearing Notifications
```javascript
// Clear all active notifications
SentryNotification.clearAll();
```

## Implementation Details
- **File location**: `core/static/core/js/notifications.js`
- **Depends on**: Toastr.js library
- **Automatically handles**: Django messages
- **Prevents**: Multiple notifications from stacking inappropriately

## Best Practices
- Always use `SentryNotification` instead of direct toastr calls.
- For form submissions, use this system instead of relying on Django messages.
- Keep notification messages concise and actionable.
- Use appropriate notification type based on message content.
- Include specific error details when possible for error messages.
- Set appropriate timeouts based on message importance.