# Project Structure Guidelines

## Directory Structure

1. Each Django app should have its own directory with the following structure:
   ```
   app_name/
       __init__.py
       admin.py
       apps.py
       models.py
       tests.py
       urls.py
       views.py
       migrations/
       static/
           app_name/
               css/
               js/
               fonts/
               img/
       templates/
           app_name/
       api/ (if needed)
       services/ (if needed)
       utils/ (if needed)
   ```

2. Static files:
   - Static files should be placed in `app_name/static/app_name/`
   - Static files should be organized by type (css, js, fonts, img)
   - Static file names should be descriptive and follow kebab-case (e.g., `alert-detail.css`)

3. Templates:
   - Templates should be placed in `app_name/templates/app_name/`
   - Base templates should be named `base.html`
   - Template names should be descriptive and follow kebab-case (e.g., `alert-detail.html`)
   - Partial templates should be placed in `app_name/templates/app_name/partials/`

4. Core functionality:
   - Shared functionality should be placed in the `core` app
   - Common templates (base, navbar, footer) should be in `core/templates/core/`
   - Shared static files should be in `core/static/core/`

## Naming Conventions

1. File names:
   - Python files: snake_case (e.g., `alert_processor.py`)
   - Static files: kebab-case (e.g., `alert-detail.css`)
   - Template files: kebab-case (e.g., `alert-detail.html`)

2. Directory names:
   - Use snake_case for Python directories
   - Use kebab-case for static/template directories

3. CSS/JS:
   - Use BEM methodology for class naming
   - Follow JavaScript ES6+ standards

## Best Practices

1. Static files:
   - Minify CSS and JavaScript in production
   - Use versioning for static files to prevent caching issues

2. Templates:
   - Use template inheritance with `{% extends %}`
   - Keep templates DRY (Don't Repeat Yourself)
   - Use template tags and filters when appropriate

3. Django-specific:
   - Use app-specific namespaces for URLs
   - Follow Django's class-based views when possible
   - Use Django's built-in form handling
   - Follow Django's security best practices