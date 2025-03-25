# Template Structure Guidelines

## Template Organization

1. Templates should be organized within app-specific directories:
   ```
   app_name/
       templates/
           app_name/
               base.html
               list.html
               detail.html
               form.html
               partials/
                   _sidebar.html
                   _pagination.html
   ```

2. Each app should have its own `base.html` that extends the project's main `base.html`

3. Template naming conventions:
   - List views: `{model_name}_list.html` or `{model_name}s.html`
   - Detail views: `{model_name}_detail.html` or `{model_name}.html`
   - Form views: `{model_name}_form.html` or `{model_name}_create_update.html`
   - Partial templates: Prefix with underscore e.g., `_sidebar.html`

4. All template names should use kebab-case format (e.g., `alert-detail.html`)

## Template Inheritance

1. Always use template inheritance with `{% extends %}`
   ```html
   {% extends "app_name/base.html" %}
   
   {% block content %}
       <!-- Page content here -->
   {% endblock %}
   ```

2. Define consistent block names across templates:
   - `title` - for page title
   - `content` - for main content
   - `extra_css` - for page-specific CSS
   - `extra_js` - for page-specific JavaScript
   - `breadcrumbs` - for breadcrumb navigation

3. Template order should be:
   - {% extends %}
   - {% load %} tags
   - {% block %} definitions

## Including Templates

1. Use {% include %} for reusable components:
   ```html
   {% include "app_name/partials/_pagination.html" with page_obj=page_obj %}
   ```

2. Pass only the required context to included templates

3. Document the expected context variables at the top of partial templates
   ```html
   {# Expected context: page_obj (Django Paginator object) #}
   ```

## Template Tags and Filters

1. Group related template tags in a single file
   ```
   app_name/
       templatetags/
           app_name_tags.py
   ```

2. Load template tags at the top of the template after extends:
   ```html
   {% extends "base.html" %}
   {% load app_name_tags %}
   ```

3. Custom template filters should be well-documented
   ```python
   @register.filter
   def custom_filter(value):
       """
       Description of what this filter does.
       
       Args:
           value: The input value to be filtered
       
       Returns:
           The transformed value
       """
       # Implementation
   ```

## Template Best Practices

1. Keep templates DRY (Don't Repeat Yourself)
2. Use comments to document complex sections
3. Limit logic in templates, prefer moving complex logic to views
4. Use URL naming and the {% url %} tag instead of hardcoded URLs
5. Use {% with %} for complex or repeated expressions
6. Use humanized output where appropriate
7. Always escape user input appropriately
8. For large templates, consider breaking into smaller components