# Minimalist Form UI/UX Guidelines (SentryHub)

## Overview
This document outlines the UI/UX design guidelines for creating clean, minimalist forms within the SentryHub application, based on the style implemented for the "Silence Rule" form.

## Core Design Principles

1.  **Clean Layout & Ample White Space:**
    *   Avoid enclosing forms within heavy containers like cards unless necessary for distinct sectioning on complex pages.
    *   Use generous margins and padding to create separation and improve readability.
    *   Employ subtle horizontal separators (`<hr>`) between distinct field groups.

2.  **Clear Typography Hierarchy:**
    *   **Page Title:** Large, bold heading (`<h2>`, `fw-bold`).
    *   **Page Subtitle:** Muted text (`<p class="text-muted">`) below the title to provide context.
    *   **Section Title:** Medium-sized, bold heading (`<h5>`, `fw-bold`) above a group of related fields.
    *   **Field Labels:** Normal font weight, placed in a dedicated column.
    *   **Help Text:** Smaller, muted text (`<p class="text-muted small mb-0">`) placed below the label.

3.  **Minimalist Components:**
    *   **Input Fields:** Remove default borders and background; use only a bottom border (`border: none; border-bottom: 1px solid #dee2e6;`). Use a subtle color change (e.g., primary blue) for the bottom border on focus. Remove default browser/framework box-shadows.
    *   **Buttons:** Use a simple, solid background button for the primary action (e.g., dark background with white text). Avoid excessive use of secondary action buttons unless essential. Remove icons from buttons for a cleaner look.
    *   **Separators:** Use a light gray, thin horizontal rule (`<hr class="form-separator">`) with reduced vertical margins (`my-2`).

4.  **Structured Two-Column Layout:**
    *   Organize form fields within rows (`<div class="row form-row-vertical-align">`).
    *   Dedicate a left column (e.g., `col-md-4`) for the label and help text.
    *   Dedicate a right column (e.g., `col-md-8`) for the input control and validation errors.
    *   Use vertical alignment (e.g., `align-items: center`) on the row to keep columns aligned.

5.  **Constrained Content Width:**
    *   For dedicated form pages, wrap the main form content within a centered, narrower column (e.g., `<div class="row justify-content-center"><div class="col-lg-10">...</div></div>`) to prevent fields from becoming excessively wide on large screens.

## Implementation Guidelines (Bootstrap 5)

### HTML Structure Example (Single Field)

```html
{# Optional: Wrap multiple fields in a centered, narrower container #}
{# <div class="row justify-content-center"> <div class="col-lg-10"> #}

<form method="post">
    {% csrf_token %}

    {# Optional: Section Title #}
    <h5 class="mb-4 fw-bold">Section Title</h5>

    {# Field Row #}
    <div class="row form-row-vertical-align">
        {# Left Column: Label & Help Text #}
        <div class="col-md-4">
            <label for="field_id" class="form-label">{{ field.label }}</label> {# Normal weight applied via CSS #}
            {% if field.help_text %}
                <p class="text-muted small mb-0">{{ field.help_text|safe }}</p>
            {% endif %}
        </div>
        {# Right Column: Input & Errors #}
        <div class="col-md-8">
            {{ field }} {# Assumes widget has 'form-control' class #}
            {% for error in field.errors %}
                <div class="invalid-feedback d-block mt-1">{{ error }}</div>
            {% endfor %}
        </div>
    </div>

    {# Separator (if more fields follow) #}
    <hr class="my-2 form-separator">

    {# ... more fields ... #}

    {# Action Buttons #}
    <div class="d-flex justify-content-end mt-5">
        <button type="submit" class="btn btn-dark-custom">Save</button>
    </div>
</form>

{# </div></div> #} {# End optional container #}
```

### CSS (`silence-rule-form.css` or similar)

```css
/* Minimalist input styling */
.form-row-vertical-align .col-md-8 .form-control,
.form-row-vertical-align .col-md-8 .form-select {
    border: none;
    border-bottom: 1px solid #dee2e6; /* Light gray bottom border */
    border-radius: 0;
    padding-left: 0;
    padding-right: 0;
    background-color: transparent;
    box-shadow: none;
}

/* Focus style */
.form-row-vertical-align .col-md-8 .form-control:focus,
.form-row-vertical-align .col-md-8 .form-select:focus {
    border-color: #0d6efd; /* Bootstrap primary */
    box-shadow: none;
    background-color: transparent;
}

/* Specific styling for SplitDateTimeWidget if used */
.split-datetime-widget {
    display: flex;
    gap: 0.3rem;
    align-items: center;
}
.split-datetime-widget input.form-control {
    padding: 0.375rem 0 !important;
    border: none;
    border-bottom: 1px solid #dee2e6;
    border-radius: 0;
    background-color: transparent;
    box-shadow: none;
    margin: 0;
    flex-grow: 1;
}
.split-datetime-widget input.form-control:focus {
    border-color: #0d6efd;
    box-shadow: none;
    background-color: transparent;
}
.form-row-vertical-align .col-md-8 .form-label.small {
    margin-bottom: 0.25rem !important;
}

/* Custom Button */
.btn-dark-custom {
    background-color: #212529; /* Bootstrap dark */
    color: #fff;
    border-radius: 0.375rem;
    padding: 0.5rem 1rem;
}
.btn-dark-custom:hover {
    background-color: #343a40;
    color: #fff;
}

/* Separator */
.form-separator {
    border-top: 1px solid #f1f3f5; /* Very light gray */
}

/* Row Layout & Alignment */
.form-row-vertical-align {
    align-items: center; /* Center items vertically */
    padding-top: 0.75rem;
    padding-bottom: 0.75rem;
}

/* Label Font Weight */
.form-row-vertical-align .col-md-4 > .form-label {
    font-weight: 400 !important; /* Normal weight */
}
```

## Usage Notes

*   Ensure the relevant CSS file is loaded in the template's `extra_css` block.
*   Apply the `form-control` class to your Django form widgets.
*   Adjust column classes (e.g., `col-md-4`, `col-md-8`, `col-lg-10`) as needed based on the specific page layout and desired responsiveness.
*   This guideline focuses on the visual style; ensure standard form validation and accessibility practices are also followed.
