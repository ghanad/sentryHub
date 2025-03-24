# SentryHub UI/UX Design Guidelines

## Overview
This document provides design guidelines to ensure consistency across the SentryHub application. Follow these standards when implementing new features or modifying existing UI components.

## Design System

### Colors
- Primary: #0d6efd (Bootstrap primary blue)
- Secondary: #6c757d (Bootstrap secondary gray)
- Success: #198754 (Bootstrap success green)
- Danger: #dc3545 (Bootstrap danger red)
- Warning: #ffc107 (Bootstrap warning yellow)
- Info: #0dcaf0 (Bootstrap info light blue)
- Light: #f8f9fa (Bootstrap light)
- Dark: #212529 (Bootstrap dark)

Always use these standard Bootstrap colors for their semantic meaning. Don't create custom colors without specific justification.

### Typography
- Font Family: 
  - Default: Bootstrap default (system fonts)
  - RTL Text: 'IranSansX', system-ui, -apple-system, 'Segoe UI', Tahoma, Arial, sans-serif
  - Code/Pre: 'Consolas', 'Monaco', 'Courier New', monospace
- Headings: Use Bootstrap's heading classes (h1-h6)
- Body text: 1rem (Bootstrap default)
- Small text: 0.875rem with class "small"
- RTL Text Properties:
  - Font weight: 400
  - Line height: 1.8
  - Letter spacing: 0
  - Text rendering: optimizeLegibility
  - Font smoothing: antialiased
  - Font features: "ss01", "ss02", "ss03", "ss04"

### Components

#### Cards
```html
<div class="card">
    <div class="card-header">
        <h5 class="card-title mb-0">Title</h5>
    </div>
    <div class="card-body">
        Content goes here
    </div>
    <div class="card-footer">
        Footer content
    </div>
</div>
```

#### Buttons
- Primary actions: `<button class="btn btn-primary">`
- Secondary actions: `<button class="btn btn-secondary">`
- Destructive actions: `<button class="btn btn-danger">`
- Use `btn-sm` for smaller buttons
- Include icons from Bootstrap Icons: `<i class="bi bi-icon-name"></i>`

#### Tables
```html
<div class="table-responsive">
    <table class="table table-hover">
        <thead>
            <tr>
                <th>Column 1</th>
                <th>Column 2</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Data 1</td>
                <td>Data 2</td>
            </tr>
        </tbody>
    </table>
</div>
```

#### Forms
```html
<form method="post">
    {% csrf_token %}
    <div class="mb-3">
        <label for="field_id" class="form-label">Field Label</label>
        <input type="text" class="form-control" id="field_id" name="field_name">
        <div class="form-text">Help text goes here</div>
    </div>
    <button type="submit" class="btn btn-primary">Submit</button>
</form>
```

#### Badges
- `<span class="badge bg-primary">Badge</span>`
- Use appropriate contextual colors

#### Alerts
- `<div class="alert alert-primary">Alert content</div>`
- Use for user notifications within the page

### Layout

#### Page Structure
- Use container-fluid for full-width layouts
- Standard pages should have:
  - Breadcrumb navigation
  - Page title (h1)
  - Content section
  - Optional action buttons aligned right

#### Breadcrumbs
```html
<nav aria-label="breadcrumb">
    <ol class="breadcrumb">
        <li class="breadcrumb-item"><a href="{% url 'home' %}">Home</a></li>
        <li class="breadcrumb-item active" aria-current="page">Current Page</li>
    </ol>
</nav>
```

#### Grid System
- Use Bootstrap's grid system with responsive breakpoints
- Standard content should be within `<div class="row"><div class="col-12"></div></div>`
- For multi-column layouts, use col-md-* for medium screens and up

### Notifications
- Use SentryNotification system as described in README_USAGE.md
- For frontend notifications, use:
```javascript
SentryNotification.success('Operation successful');
SentryNotification.error('Error message');
SentryNotification.warning('Warning message');
SentryNotification.info('Information message');
```

### Navigation
- Main navigation in navbar
- Admin actions should be in the Admin dropdown
- Section-specific actions should be in card headers or page headers

### Icons
- Use Bootstrap Icons (bi-*) consistently
- Common usages:
  - Add: bi-plus-circle
  - Edit: bi-pencil
  - Delete: bi-trash
  - View: bi-eye
  - Back: bi-arrow-left
  - Alert: bi-exclamation-triangle
  - Info: bi-info-circle

## Templates Structure
- Extend base templates: `{% extends "alerts/base.html" %}`
- Use blocks for content: `{% block content %}{% endblock %}`
- Include partials for reusable components
- Use consistent naming for template files

## Responsive Design
- All pages must be responsive
- Use Bootstrap utility classes for responsive behavior
- Test on mobile, tablet and desktop viewports

## Accessibility
- Use semantic HTML elements
- Include aria-labels where appropriate
- Maintain sufficient color contrast
- Ensure keyboard navigability

## Examples
See existing templates in the project for reference:
- List view: alerts/templates/alerts/alert_list.html
- Detail view: alerts/templates/alerts/alert_detail.html
- Form: docs/templates/docs/documentation_form.html

## Data Visualization

### Charts and Graphs
- Use Chart.js for all data visualization
- Follow this pattern for implementation:
```html
<div class="chart-container" style="height: 300px;">
    <canvas id="myChart"></canvas>
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
    const ctx = document.getElementById('myChart').getContext('2d');
    const chart = new Chart(ctx, {
        type: 'line',  // or 'bar', 'pie', etc.
        data: {
            labels: ['Label 1', 'Label 2'],
            datasets: [{
                label: 'Dataset Name',
                data: [1, 2],
                backgroundColor: '#0d6efd',
                borderColor: '#0d6efd'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
});
</script>
```

### Tables with Data
- For complex data tables, include:
  - Pagination
  - Sorting options
  - Filtering
  - Empty state handling

```html
<!-- Empty State Example -->
{% if items|length == 0 %}
<div class="text-center py-5">
    <i class="bi bi-inbox display-4 text-muted"></i>
    <p class="mt-3 text-muted">No data available</p>
</div>
{% endif %}
```

## Loading States
- Use spinner for loading states:
```html
<div class="text-center p-5">
    <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Loading...</span>
    </div>
    <p class="mt-2">Loading...</p>
</div>
```

## Modals
- Use Bootstrap modals for confirmations and small forms:
```html
<div class="modal fade" id="exampleModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Modal Title</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body">
                Modal content goes here
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                <button type="button" class="btn btn-primary">Save</button>
            </div>
        </div>
    </div>
</div>
```

## Page-Specific Patterns

### List Pages
- Include:
  - Search/filter functionality
  - Pagination
  - Action buttons (top-right)
  - Consistent table structure
  - Links to detail pages

### Detail Pages
- Organize with tabs for complex objects
- Put primary actions in the header
- Use cards to group related information
- Include breadcrumb navigation

### Form Pages
- Form validation should show errors inline
- Required fields marked with asterisk
- Cancel button alongside submit button
- Consistent button positioning (right-aligned)

## Testing Your UI
Before submitting UI changes, verify:
1. Responsive behavior works on different screen sizes
2. All interactive elements are functional
3. Design is consistent with existing pages
4. Notifications appear correctly
5. Error states and validation are handled properly

## Common Patterns by Function

### Actions Menu
For item actions in tables or detail views:
```html
<div class="dropdown">
    <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown">
        Actions
    </button>
    <ul class="dropdown-menu dropdown-menu-end">
        <li><a class="dropdown-item" href="#"><i class="bi bi-eye me-2"></i>View</a></li>
        <li><a class="dropdown-item" href="#"><i class="bi bi-pencil me-2"></i>Edit</a></li>
        <li><hr class="dropdown-divider"></li>
        <li><a class="dropdown-item text-danger" href="#"><i class="bi bi-trash me-2"></i>Delete</a></li>
    </ul>
</div>
```

### Search Components
```html
<form method="get" class="mb-4">
    <div class="input-group">
        <input type="text" class="form-control" placeholder="Search..." name="search" value="{{ search_query }}">
        <button class="btn btn-primary" type="submit">
            <i class="bi bi-search"></i> Search
        </button>
    </div>
</form>
```

### Tabs Navigation
```html
<ul class="nav nav-tabs" id="myTab" role="tablist">
    <li class="nav-item" role="presentation">
        <button class="nav-link active" id="tab1-tab" data-bs-toggle="tab" data-bs-target="#tab1" type="button" role="tab" aria-selected="true">
            Tab 1
        </button>
    </li>
    <li class="nav-item" role="presentation">
        <button class="nav-link" id="tab2-tab" data-bs-toggle="tab" data-bs-target="#tab2" type="button" role="tab" aria-selected="false">
            Tab 2
        </button>
    </li>
</ul>
<div class="tab-content" id="myTabContent">
    <div class="tab-pane fade show active" id="tab1" role="tabpanel">
        Tab 1 content
    </div>
    <div class="tab-pane fade" id="tab2" role="tabpanel">
        Tab 2 content
    </div>
</div>
```

## Final Notes
The goal of these guidelines is to maintain a consistent, user-friendly interface throughout SentryHub. When adding new features, reference existing components and patterns before creating new ones. 

Always prioritize:
- Consistency with existing UI
- Responsiveness across devices
- Intuitive user experience
- Accessibility
- Performance

For questions or clarifications about these guidelines, refer to the existing codebase as the source of truth for UI/UX patterns.

## User Feedback and Error Handling

### Form Validation
- Display validation errors inline with form fields
- Use Bootstrap's validation classes
```html
<div class="mb-3">
    <label for="username" class="form-label">Username</label>
    <input type="text" class="form-control {% if form.username.errors %}is-invalid{% endif %}" id="username" name="username">
    {% if form.username.errors %}
    <div class="invalid-feedback">
        {% for error in form.username.errors %}{{ error }}{% endfor %}
    </div>
    {% endif %}
</div>
```

### Error Pages
- Create consistent error pages for 404, 500, etc.
- Include navigation back to safe areas of the application
```html
<div class="text-center py-5">
    <h1 class="display-1">404</h1>
    <p class="lead">Page not found</p>
    <p>The requested page could not be found.</p>
    <a href="{% url 'alerts:dashboard' %}" class="btn btn-primary">
        <i class="bi bi-house"></i> Return to Dashboard
    </a>
</div>
```

### Empty States
- Always design for empty states
- Provide helpful guidance to users
```html
<div class="text-center py-5">
    <i class="bi bi-clipboard-x display-4 text-muted"></i>
    <h5 class="mt-3">No alerts found</h5>
    <p class="text-muted">There are no alerts matching your criteria.</p>
    <a href="{% url 'alerts:dashboard' %}" class="btn btn-outline-primary">
        Return to Dashboard
    </a>
</div>
```

## Themes and Customization

### Dark/Light Mode
- The application currently uses light mode only
- If implementing dark mode in the future, use CSS variables and the `data-bs-theme` attribute

### RTL Support
- Some content may need RTL (Right-to-Left) support
- Use the following pattern for RTL text detection and styling:
```javascript
function isPersianText(text) {
    // Persian Unicode range: \u0600-\u06FF
    // Arabic Unicode range: \u0750-\u077F
    // Arabic Supplement range: \u0870-\u089F
    // Arabic Extended-A range: \u08A0-\u08FF
    // Arabic Presentation Forms-A: \uFB50-\uFDFF
    // Arabic Presentation Forms-B: \uFE70-\uFEFF
    const rtlRegex = /[\u0600-\u06FF\u0750-\u077F\u0870-\u089F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]/;
    return rtlRegex.test(text);
}

function setTextDirection(element) {
    if (isPersianText(element.textContent)) {
        element.style.direction = 'rtl';
        element.style.textAlign = 'right';
        element.style.fontFamily = "'IranSansX', system-ui, -apple-system, 'Segoe UI', Tahoma, Arial, sans-serif";
        element.style.fontWeight = '400';
        element.style.lineHeight = '1.8';
        element.style.letterSpacing = '0';
        element.style.textRendering = 'optimizeLegibility';
        element.style.webkitFontSmoothing = 'antialiased';
        element.style.mozOsxFontSmoothing = 'grayscale';
        element.style.fontFeatureSettings = '"ss01", "ss02", "ss03", "ss04"';
        element.classList.add('rtl-text');
    } else {
        element.style.direction = 'ltr';
        element.style.textAlign = 'left';
        element.style.fontFamily = '';
        element.style.fontWeight = '';
        element.style.lineHeight = '';
        element.style.letterSpacing = '';
        element.style.textRendering = '';
        element.style.webkitFontSmoothing = '';
        element.style.mozOsxFontSmoothing = '';
        element.style.fontFeatureSettings = '';
        element.classList.remove('rtl-text');
    }
}

// Apply to elements with data-rtl="true" attribute
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('[data-rtl="true"]').forEach(setTextDirection);
});
```

For TinyMCE editor configuration:
```python
TinyMCE(
    attrs={'class': 'form-control'},
    mce_attrs={
        'directionality': 'rtl',
        'content_style': '''
            body {
                font-family: 'IranSansX', system-ui, -apple-system, 'Segoe UI', Tahoma, Arial, sans-serif;
                font-weight: 400;
                line-height: 1.8;
                letter-spacing: 0;
                text-rendering: optimizeLegibility;
                -webkit-font-smoothing: antialiased;
                -moz-osx-font-smoothing: grayscale;
                font-feature-settings: "ss01", "ss02", "ss03", "ss04";
            }
        ''',
        # ... other TinyMCE settings ...
    }
)
```

Special considerations for RTL content:
1. Code blocks and pre elements should always be LTR
2. Tables should maintain their structure regardless of text direction
3. Images and media should be properly aligned based on content direction
4. Lists (ordered and unordered) should respect RTL direction
5. Blockquotes should have border on the appropriate side based on direction

## JavaScript Patterns

### Event Handling
- Use event delegation where possible
- Attach handlers using addEventListener
```javascript
document.addEventListener('DOMContentLoaded', function() {
    // DOM is ready
    document.querySelector('#parentElement').addEventListener('click', function(e) {
        if (e.target.matches('.button-class')) {
            // Handle the event
        }
    });
});
```

### AJAX Requests
- Use the fetch API for AJAX requests
```javascript
fetch('/api/endpoint/', {
    method: 'POST',
    body: JSON.stringify(data),
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
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

### Animation and Transitions
- Use Bootstrap's fade classes for simple transitions
- Keep animations subtle and purposeful
- Ensure animations can be disabled for accessibility preferences

## Printable Views
For views that might be printed:
```html
<div class="d-print-none">
    <!-- Content visible only on screen, not when printing -->
</div>
<div class="d-none d-print-block">
    <!-- Content visible only when printing -->
</div>
```

## Performance Considerations
- Optimize image sizes
- Minimize DOM depth
- Avoid unnecessary markup
- Use pagination for large data sets
- Defer loading of non-critical resources

## Documentation Within Templates
- Comment complex sections of templates
- Include docstrings in template tags
- Document JavaScript functions

## Component Evolution
When a component needs to evolve:
1. Check if it's used elsewhere in the application
2. Determine if changes should be applied globally
3. If a new pattern is needed, document the rationale
4. Update this guide if necessary

## Design Resources
- Use Bootstrap Icons: https://icons.getbootstrap.com/
- Bootstrap Documentation: https://getbootstrap.com/docs/5.1/
- Color contrast checker: https://webaim.org/resources/contrastchecker/

## Checklist for New Pages

Before considering a new UI feature complete, verify it meets these requirements:

- [ ] Follows established layout patterns
- [ ] Uses existing components where appropriate
- [ ] Includes proper navigation (breadcrumbs, links)
- [ ] Handles all states (loading, empty, error)
- [ ] Works responsively on mobile, tablet, and desktop
- [ ] Includes appropriate feedback for user actions
- [ ] Error states are handled gracefully
- [ ] Accessibility considerations addressed
- [ ] Documentation for complex interactions
- [ ] Consistent with the rest of the application
- [ ] Performance considerations addressed

By following these guidelines, we can maintain a consistent, user-friendly interface throughout the SentryHub application, regardless of which contributor is implementing new features or modifying existing ones.

## Implementation Best Practices

### Template Organization
- Use template inheritance consistently:
  - Base templates define the overall structure
  - Child templates extend base templates
  - Partial templates for reusable components

### CSS Organization
- Follow Bootstrap conventions
- Custom CSS should be organized by component
- Use utility classes when appropriate
- Avoid inline styles except for dynamic values

### JavaScript Integration
- Keep JavaScript in separate files
- Use unobtrusive JavaScript where possible
- Load scripts at the end of the body
- Document complex JavaScript functions

### Integration with Django
- Use Django template tags consistently
- Follow naming conventions for URLs
- Leverage context processors for global data
- Use Django forms with Bootstrap styling

## Accessibility Implementation
- Ensure proper heading hierarchy (h1, h2, etc.)
- Use aria attributes appropriately
- Ensure sufficient color contrast
- Provide text alternatives for non-text content
- Make sure all interactive elements are keyboard accessible

## Component Library Reference

This section provides a quick reference to common components used throughout SentryHub:

### Page Layout
```html
{% extends "alerts/base.html" %}

{% block title %}Page Title - SentryHub{% endblock %}

{% block content %}
<div class="row mb-4">
    <div class="col-12">
        <nav aria-label="breadcrumb">
            <ol class="breadcrumb">
                <li class="breadcrumb-item"><a href="{% url 'alerts:dashboard' %}">Dashboard</a></li>
                <li class="breadcrumb-item active">Current Page</li>
            </ol>
        </nav>
    </div>
</div>

<div class="row mb-4">
    <div class="col-12">
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h5 class="mb-0">Page Title</h5>
                <a href="#" class="btn btn-primary">
                    <i class="bi bi-plus-circle"></i> Action Button
                </a>
            </div>
            <div class="card-body">
                <!-- Main content goes here -->
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

## Versioning and Updates

This guide represents the current UI/UX standards for SentryHub. As the application evolves:

1. New patterns may be established
2. Existing patterns may be refined
3. This documentation should be updated accordingly

When proposing UI changes that don't follow these guidelines:
1. Provide rationale for the deviation
2. Consider if the change should become a new standard
3. Update this documentation if a new standard is established

## Conclusion

Maintaining consistency in UI/UX design is crucial for providing a good user experience. These guidelines serve as a reference to ensure that all parts of SentryHub maintain a cohesive look and feel, regardless of when they were implemented or by whom.

By following these standards, we can:
- Reduce development time through reuse of patterns
- Improve usability through consistency
- Ensure accessibility across the application
- Maintain a professional and polished appearance

Remember that these guidelines are not meant to restrict creativity, but rather to provide a framework that ensures a consistent user experience throughout the application.

When in doubt, refer to existing implementations and this documentation to guide your UI/UX decisions.
