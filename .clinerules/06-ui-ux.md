# UI/UX Guidelines - Tables

This document outlines the standard structure and styling for data tables within the SentryHub application to ensure consistency and a good user experience.

## 1. Basic Structure

All data tables should follow this basic HTML structure, utilizing Bootstrap 5 classes and custom application classes:

```html
<!-- Optional: Filter/Search Section (See Section 7) -->
<div class="filter-section mb-4">
    <!-- Filter form elements -->
</div>
<!-- OR -->
<div class="chart-card filter-card mb-4">
    <div class="chart-card-body">
        <!-- Filter form elements -->
    </div>
</div>


<!-- Main Table Card -->
<div class="chart-card">
    <div class="chart-card-header">
        <h5 class="chart-title d-flex align-items-center gap-2">
            <i data-lucide="list-ul"></i> <!-- Use relevant Lucide icon -->
            Table Title
            {% if is_paginated %}
               <span class="badge bg-secondary rounded-pill fw-normal ms-2">Page {{ page_obj.number }} of {{ page_obj.paginator.num_pages }}</span>
            {% endif %}
        </h5>
         <span class="text-muted small">Total: {{ page_obj.paginator.count }}</span> {# Or other relevant info #}
    </div>
    <div class="chart-card-body p-0"> {# Use p-0 to remove padding around the table #}
        <div class="table-responsive">
            <table class="alert-table"> {# Standard table class #}
                <thead>
                    <tr>
                        <th class="col-identifier">Identifier</th> {# Use specific column classes #}
                        <th class="col-status">Status</th>
                        <th class="col-date">Date</th>
                        <th class="col-actions text-end">Actions</th> {# Align actions right if desired #}
                        <!-- Add other headers as needed -->
                    </tr>
                </thead>
                <tbody>
                    {% for item in items %}
                    <tr>
                        <td class="col-identifier">
                            <a href="{# item detail url #}" class="alert-name-link">{{ item.name }}</a> {# Link primary identifier #}
                        </td>
                        <td class="col-status">
                            {# Use status badges (See Section 4) #}
                        </td>
                        <td class="col-date">
                            {# Use date formatting (See Section 5) #}
                        </td>
                        <td class="col-actions text-end"> {# Align actions right if desired #}
                            {# Use action menu (See Section 3) #}
                        </td>
                        <!-- Add other data cells as needed -->
                    </tr>
                    {% empty %}
                    <tr>
                        <td colspan="[NUMBER_OF_COLUMNS]" class="text-center p-5"> {# Standard empty state #}
                            <i data-lucide="info" class="fs-1 text-muted mb-3 d-block"></i> {# Use relevant icon #}
                            <p class="text-muted mb-0">No items found.</p> {# Adjust text as needed #}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        <!-- Pagination -->
        {% if is_paginated %}
            {% include 'core/partials/_pagination.html' with page_obj=page_obj %}
        {% endif %}
    </div>
</div>
```

## 2. Styling and Classes

*   **Container:** Always wrap tables within a `div.chart-card`.
*   **Table Class:** Use the standard `table.alert-table` class for all data tables. This allows for consistent base styling.
*   **Responsiveness:** Always wrap the `<table>` element within a `div.table-responsive` to handle smaller screens gracefully.
*   **Column Classes:**
    *   Assign specific, descriptive CSS classes to both `<th>` and `<td>` elements (e.g., `col-name`, `col-status`, `col-updated`, `col-actions`).
    *   Avoid using inline `style` attributes for widths or other styling. Define column widths and other styles in the relevant CSS file (e.g., `alerts/css/alerts_list.css`) targeting these classes.
*   **Text Alignment:** Use Bootstrap text alignment classes (e.g., `text-center`, `text-end`) on `<th>` or `<td>` where appropriate, especially for numerical data or actions.

## 3. Actions Column

*   Place user actions (View, Edit, Delete, etc.) in the last column (`th/td.col-actions`).
*   Group actions within a `div.action-menu`. This div should use Flexbox (`d-flex`, `gap-2`, etc.) for layout, defined globally or in `modern_dashboard.css`.
*   Represent actions as links (`<a>`) styled as icon buttons using the `action-btn` class.
*   Use Lucide icons (`<i>` tags with `data-lucide` attribute) within the action buttons.
*   Always include tooltips (`data-bs-toggle="tooltip" title="..."`) to clarify the action button's purpose.
*   For destructive actions like "Delete", use a confirmation mechanism (e.g., a JavaScript confirmation dialog or a Bootstrap modal) triggered by the button/link. Refer to `users/templates/users/user_list.html` for a modal example.
*   **Combining Tooltips and Modals:** If an action button needs to *both* trigger a modal (`data-bs-toggle="modal"`) and display a tooltip (`data-bs-toggle="tooltip"`), place the tooltip attributes on a wrapper `<span>` element around the button. This avoids conflicts between the two Bootstrap JavaScript triggers.
    ```html
    <span data-bs-toggle="tooltip" title="Your Tooltip Text">
        <button type="button" class="action-btn" data-bs-toggle="modal" data-bs-target="#yourModalId">
            <i data-lucide="your-icon"></i>
        </button>
    </span>
    ```

## 4. Badges

*   Use Bootstrap badges (`span.badge`) for concise status indicators (e.g., Firing/Resolved, Active/Expired, Yes/No, severity levels, counts).
*   Prefer `rounded-pill` for badge shape (`span.badge.rounded-pill`).
*   Define consistent, application-specific status classes (e.g., `status-badge status-critical`, `status-badge status-active`, `status-badge status-resolved`) in a shared CSS file (`modern_dashboard.css` or similar) to ensure uniform appearance.
*   Include relevant icons within badges where appropriate (e.g., `<i data-lucide="circle"></i> Firing`).

## 5. Dates and Times

*   Display dates and times relevant to the user's perspective using the `|time_ago` template tag for brevity (e.g., "5 minutes ago", "2 days ago").
*   Provide the full, localized timestamp in a tooltip using the `|format_datetime:user` template tag. Wrap the `time_ago` output in a `<span>` with the tooltip attributes:
    ```html
    <span data-bs-toggle="tooltip" title="{{ item.timestamp|format_datetime:user }}">
        {{ item.timestamp|time_ago }}
    </span>
    ```

## 6. Links

*   Make the primary identifier in each row (e.g., username, alert name, documentation title) a clickable link leading to its detail or edit page.
*   Apply the `alert-name-link` class to these primary links for consistent styling.

## 7. Filter/Search Sections

*   Place filter or search controls *above* the main `div.chart-card` containing the table.
*   Use either a simple `div.filter-section.mb-4` or wrap the controls in their own `div.chart-card.filter-card.mb-4` for visual grouping, depending on complexity.
*   Use standard Bootstrap form controls (`form-label`, `form-control`, `form-select`, `btn`, etc.).
*   Include "Apply" / "Search" and "Clear" / "Reset" buttons.

## 8. Empty State

*   When the table has no data (either initially or after filtering), display a clear message within the `<tbody>`.
*   Use the `{% empty %}` tag within the loop or conditional logic in the view to render this state.
*   The empty state should be a single row spanning all columns (`<td colspan="[NUMBER_OF_COLUMNS]">`).
*   Center the content (`text-center`) and add padding (`p-5`).
*   Include a relevant Lucide icon and a descriptive text message (e.g., "No alerts found matching your criteria.", "No users available.").

By adhering to these guidelines, we can ensure all tables across the application share a consistent look, feel, and behavior, improving the overall user experience.

## 9. Building Pages with the Modern UI

Whether creating a new page or migrating an existing one, follow these standards to ensure consistency with the modern SentryHub look and feel:

1.  **Use Modern Base Template:** All pages using the modern UI *must* extend the correct base template:
   ```html
   {% extends "main_dashboard/base_modern.html" %}
   ```
2.  **Update Block Names:** Ensure you are using the correct block names defined in `base_modern.html`. The primary content block is typically `{% block main_content %}`. Replace older block names like `{% block content %}`. Check `main_dashboard/base_modern.html` for other available blocks (e.g., `extra_css`, `extra_js`).
3.  **Adopt Modern Structure:** Refactor the page content to use the standard structures outlined in this guideline:
   *   Use `<header class="page-header">` for page titles (See Section 1 example).
   *   Wrap main content sections (like tables, forms, stats) in `<div class="chart-card">` elements (See Section 1).
   *   Implement tables following the structure in Section 1, using `div.table-responsive` and `table.alert-table`.
4.  **Apply Standard Classes:** Replace any old or custom CSS classes with the standard classes defined in this guideline and `modern_dashboard.css`:
   *   Use `chart-card`, `chart-card-header`, `chart-card-body`, `chart-title`.
   *   Use `alert-table`, `col-*` classes for table columns (See Section 2).
   *   Use `action-menu` and `action-btn` for table actions (See Section 3).
   *   Use `status-badge` classes for badges (See Section 4).
   *   Use the standard date formatting pattern (See Section 5).
   *   Use `alert-name-link` for primary links (See Section 6).
   *   Structure filters/search using the patterns in Section 7.
5.  **Rely on Standard CSS:** Ensure styling primarily comes from the CSS included via `base_modern.html` (like Bootstrap and `modern_dashboard.css`). Avoid adding page-specific CSS files unless absolutely necessary for unique components not covered by the standard styles. If migrating, remove links to old, redundant CSS files.
6.  **Verify Consistency:** Review the updated page against other modern pages (like Acknowledgements or the Main Dashboard) to ensure visual and functional consistency.

## 10. Iconography

SentryHub utilizes **Lucide Icons** for all modern UI icons. When adding new icons or replacing existing ones, always use Lucide icons.

*   **Integration:** Lucide icons are integrated via a script tag in `dashboard/templates/dashboard/base.html`.
*   **Usage:** Icons are typically used with the `data-lucide="icon-name"` attribute on an `<i>` tag or directly as an SVG.
*   **Sizing:** Ensure icons are appropriately sized using CSS classes like `nav-icon` or `fs-4`, or by directly setting `width` and `height` on the SVG element if necessary. Refer to `dashboard/static/dashboard/css/modern_dashboard_base.css` for icon sizing rules.
*   **Accessibility:** Always consider accessibility when using icons. If an icon conveys meaning without accompanying text, ensure it has an appropriate `aria-label` or `title` attribute.