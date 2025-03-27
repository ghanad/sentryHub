# SentryHub UI/UX Design Guidelines

## 1. Overview

This document provides general UI/UX design guidelines to ensure consistency, usability, and a clean aesthetic across the SentryHub application. Follow these standards when implementing new features or modifying existing UI components. The goal is to create an intuitive, efficient, and visually cohesive experience.

## 2. Core Design Philosophy

*   **Consistency:** Use established patterns, components, and styles throughout the application. Refer to Bootstrap 5 documentation and these guidelines.
*   **Clarity:** Ensure information is presented clearly and actions are unambiguous. Prioritize readability and intuitive navigation.
*   **Simplicity:** Avoid unnecessary clutter. Strive for clean layouts with ample whitespace.
*   **Responsiveness:** All interfaces must adapt gracefully to different screen sizes (desktop, tablet, mobile).
*   **Accessibility:** Follow WCAG guidelines to ensure usability for all users. Use semantic HTML, provide alt text, ensure keyboard navigation, and maintain sufficient contrast.

## 3. Design System

### 3.1. Colors

*   Utilize Bootstrap 5's standard semantic colors for their intended purpose:
    *   Primary: `#0d6efd` (Links, primary actions)
    *   Secondary: `#6c757d` (Secondary text, less important elements)
    *   Success: `#198754` (Success messages, confirmations)
    *   Danger: `#dc3545` (Errors, destructive actions, critical alerts)
    *   Warning: `#ffc107` (Warnings, non-critical issues)
    *   Info: `#0dcaf0` (Informational messages, neutral highlights)
    *   Light: `#f8f9fa` (Backgrounds, card headers)
    *   Dark: `#212529` (Text, primary dark elements, navbar)
*   Use utility classes (`text-primary`, `bg-danger`, etc.) for applying colors.

### 3.2. Typography

*   **Default Font:** Bootstrap 5 default (system font stack: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol"`).
*   **Persian/RTL Font:** 'IranSansX' (See `.clinerules/07-persian-fonts.md` and `core/static/core/css/fonts.css`). Use the `rtl-text` class or automatic detection via JS where appropriate.
*   **Code Font:** `SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace`. Use `<code>` or `<pre>` tags or the `.font-monospace` class.
*   **Headings:** Use standard `<h1>` to `<h6>` tags and Bootstrap heading classes (`.h1` to `.h6`, `.display-*`). Ensure logical hierarchy.
*   **Body Text:** Default Bootstrap size (usually 1rem).
*   **Small Text:** Use the `<small>` tag or `.small` class (`0.875em`).
*   **Links:** Standard Bootstrap link styling (primary color, underline on hover).

### 3.3. Layout

*   **Structure:** Maintain a consistent global structure: Navbar, Main Content Area, Footer (optional).
*   **Containers:** Use `.container-fluid` for full-width sections (like Navbar) and `.container` for centered, max-width content areas.
*   **Grid System:** Utilize Bootstrap's 12-column grid (`.row`, `.col-*`, `.col-md-*`, etc.) for arranging content.
*   **Spacing:** Use Bootstrap spacing utilities (`m-*, p-*, gap-*`) for consistent margins and padding.
*   **Whitespace:** Allow ample whitespace around elements to improve readability and reduce clutter.
*   **Breadcrumbs:** Use standard Bootstrap breadcrumbs for navigation hierarchy on nested pages.
    ```html
    <nav aria-label="breadcrumb">
        <ol class="breadcrumb">
            <li class="breadcrumb-item"><a href="...">Home</a></li>
            <li class="breadcrumb-item active" aria-current="page">Current Page</li>
        </ol>
    </nav>
    ```

### 3.4. Icons

*   **Primary Icon Set:** [Bootstrap Icons](https://icons.getbootstrap.com/). Use the `<i>` tag with appropriate classes (e.g., `<i class="bi bi-pencil"></i>`).
*   **Consistency:** Use icons consistently for similar actions (e.g., `bi-pencil` for edit, `bi-trash` for delete, `bi-plus-circle` for add/create, `bi-eye` for view).
*   **Placement:** Typically place icons *before* button text, separated by a small margin (`me-1` or `me-2`).

### 3.5. Components

*   **Cards:** Use `.card` for grouping related content. Use `.card-header`, `.card-body`, `.card-footer` as needed. Keep styling minimal (light header background, subtle shadow).
*   **Buttons:**
    *   Use semantic button classes (`.btn-primary`, `.btn-danger`, `.btn-secondary`).
    *   Use `.btn-sm` for table actions or less prominent buttons.
    *   Use outline buttons (`.btn-outline-*`) for secondary actions.
    *   Consider the custom `.btn-dark-custom` for primary save/submit actions in forms (as defined in `standard-form.css`).
*   **Tables:**
    *   Use `.table` class. Add `.table-hover` for row highlighting.
    *   Wrap tables in `.table-responsive` for smaller screens.
    *   Use `.table-striped` for better row distinction in dense tables.
    *   Keep table headers (`<thead>`) clear and concise. Use `.table-light` for header background.
*   **Badges:** Use `.badge` with background color utilities (`.bg-*`) for status indicators, counts, or tags.
*   **Alerts (Bootstrap):** Use `.alert` with contextual classes (`.alert-success`, `.alert-danger`, etc.) for static messages *within* the page content. Note: For dynamic user feedback (form submissions, etc.), use the Toastr system.
*   **Modals:** Use Bootstrap modals (`.modal`) for confirmations, quick edits, or short forms.
*   **Pagination:** Use the standard Bootstrap pagination component (`.pagination`). Include logic for first/last, previous/next, and a limited range of page numbers. (See `core/templates/core/partials/_pagination.html`).

## 4. Specific Patterns

### 4.1. Forms (Standard Style V2)

This is the **preferred style** for most forms (creation, editing).

*   **Layout:** Use the two-column layout with an offset gap, contained within a `.form-container` on a white background.
    *   Outer Wrapper: `<div class="row justify-content-center"><div class="col-lg-10 col-xl-9">...</div></div>`
    *   Form Wrapper: `<div class="form-container">...</div>`
    *   Field Row: `<div class="row form-row-layout">`
        *   Label Column: `<div class="col-md-4">` (contains `<label>` and `<p class="form-help-text">`)
        *   Input Column: `<div class="col-md-7 offset-md-1">` (contains input widget and error messages)
*   **Styling:** Apply styles defined in `core/static/core/css/standard-form.css`.
    *   Standard `.form-control` / `.form-select` appearance.
    *   Thin, light separators (`<hr class="form-separator">`) between each field row.
    *   Primary action button (`.btn-dark-custom`) aligned to the bottom-right.
*   **Titles:** Use `.page-title` / `.page-subtitle` outside the container and `.section-title` inside.
*   **Implementation:** Refer to the HTML structure and CSS rules defined in `core/static/core/css/standard-form.css`. Ensure Django form widgets use the `.form-control` class.

### 4.2. Notifications (User Feedback)

*   Use the `SentryNotification` JavaScript object (wrapper around Toastr) for dynamic user feedback (e.g., after form submission, AJAX success/error). See `.clinerules/05-notification.md`.
*   Methods: `SentryNotification.success('Message')`, `.error()`, `.warning()`, `.info()`.
*   Avoid using standard Bootstrap alerts (`_messages.html`) for feedback that should automatically disappear or is triggered by JavaScript actions. Configure templates to either show *only* Toastr or *only* Bootstrap alerts for a given message, not both.

### 4.3. Loading States

*   Use Bootstrap spinners (`.spinner-border` or `.spinner-grow`) to indicate loading or processing states, especially during AJAX requests.
    ```html
    <div class="text-center p-3">
        <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
    </div>
    ```

### 4.4. Empty States

*   Provide clear and helpful messages when lists or tables are empty. Include an relevant icon and potentially a call to action.
    ```html
    <div class="text-center p-5">
        <i class="bi bi-inbox display-4 text-muted"></i>
        <p class="mt-3 text-muted">No items found.</p>
        <a href="..." class="btn btn-primary">Create First Item</a>
    </div>
    ```

### 4.5. Form Validation

*   Display validation errors clearly below the respective input field using Bootstrap's `.invalid-feedback` class (ensure it's set to `d-block` if needed).
*   Use the `.is-invalid` class on the input field to trigger error styling.
*   Provide helpful error messages.

## 5. Responsiveness

*   Design mobile-first where practical.
*   Use Bootstrap's responsive grid and utility classes extensively (`d-none d-md-block`, `text-center text-md-start`, etc.).
*   Test layouts thoroughly on various screen sizes. Ensure tables are scrollable (`.table-responsive`) and forms reflow correctly.

## 6. Accessibility (A11y)

*   Use semantic HTML elements (`<nav>`, `<main>`, `<header>`, `<footer>`, `<button>`).
*   Provide `alt` text for all meaningful images.
*   Use `aria-label` or `aria-labelledby` for elements needing clarification (e.g., icon-only buttons).
*   Ensure sufficient color contrast between text and background.
*   Ensure all interactive elements are focusable and operable via keyboard.
*   Use form labels correctly associated with their inputs (`for` attribute).

## 7. RTL Support

*   Use the `IranSansX` font family for Persian text (loaded via `fonts.css`).
*   Apply `direction: rtl; text-align: right;` to elements containing primarily Persian text. Use the `rtl-text` class or the JavaScript detection logic in `rtl-text.js`.
*   Be mindful of layout mirroring for components like dropdown menus, icons within buttons, etc. Code blocks (`<pre>`, `<code>`) should generally remain LTR.

## 8. Code Implementation

*   **Templates:** Use Django's template inheritance (`{% extends %}`, `{% block %}`). Organize reusable snippets into partials (`{% include %}`). Use the `{% static %}` tag for static files and `{% url %}` for URLs.
*   **CSS:** Organize CSS into app-specific files (`app/static/app/css/`) and core/shared files (`core/static/core/css/`). Follow BEM naming conventions where appropriate for custom components. Leverage Bootstrap utility classes first.
*   **JavaScript:** Keep JS in separate files. Use unobtrusive JS (attach event listeners rather than using inline `onclick`). Use `fetch` for AJAX. Reference the `SentryNotification` object for user feedback.

## 9. Versioning

This document reflects the current standards. As the application evolves, these guidelines may be updated. Major style changes should be documented and agreed upon.