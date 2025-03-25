# Static Files Structure Guidelines

## Directory Structure

1. Static files should be organized within app-specific directories:
   ```
   app_name/
       static/
           app_name/
               css/
                   app_name.css
                   template-name.css
               js/
                   app_name.js
                   template-name.js
               img/
                   logo.png
                   icons/
               fonts/
   ```

2. Each template should have corresponding CSS and JS files with the same name:
   - Template: `app_name/templates/app_name/template-name.html`
   - CSS: `app_name/static/app_name/css/template-name.css`
   - JS: `app_name/static/app_name/js/template-name.js`

3. Shared static files should be placed in the `core` app:
   ```
   core/
       static/
           core/
               css/
                   base.css
                   forms.css
               js/
                   base.js
                   notifications.js
               img/
                   logo.png
                   favicon.ico
   ```

## Naming Conventions

1. All static file names should use kebab-case:
   - CSS: `template-name.css`, `user-profile.css`
   - JS: `template-name.js`, `chart-helpers.js`
   - Images: `header-background.png`, `user-avatar.jpg`

2. CSS classes should follow BEM (Block, Element, Modifier) methodology:
   - Block: `.alert`
   - Element: `.alert__title`, `.alert__content`
   - Modifier: `.alert--warning`, `.alert--danger`

3. JavaScript:
   - Functions and variables: camelCase
   - Classes: PascalCase
   - Constants: UPPER_SNAKE_CASE

## CSS Guidelines

1. Organize CSS in a logical order:
   - Reset/normalize
   - Base elements
   - Components
   - Utilities

2. Use CSS variables for consistent theming:
   ```css
   :root {
     --primary-color: #0d6efd;
     --secondary-color: #6c757d;
     --success-color: #198754;
     --danger-color: #dc3545;
   }
   ```

3. Use responsive design principles:
   - Mobile-first approach
   - Use relative units (em, rem, %) over fixed units (px)
   - Test designs on multiple screen sizes

4. Avoid deep nesting of selectors

## JavaScript Guidelines

1. Organize code by functionality:
   - Core utilities
   - UI components
   - Page-specific logic

2. Use modern JavaScript (ES6+) features:
   - Arrow functions
   - Template literals
   - Destructuring
   - Async/await for asynchronous operations

3. Handle errors properly:
   ```javascript
   try {
     // Code that might fail
   } catch (error) {
     console.error('Error:', error);
     SentryNotification.error('An error occurred');
   }
   ```

4. Document complex functions:
   ```javascript
   /**
    * Fetches data from the API and updates the UI
    * @param {string} endpoint - The API endpoint to fetch
    * @param {Object} options - Additional fetch options
    * @returns {Promise<void>}
    */
   async function fetchData(endpoint, options = {}) {
     // Implementation
   }
   ```

## Image Guidelines

1. Use appropriate file formats:
   - JPG/JPEG for photographs
   - PNG for images with transparency
   - SVG for icons and logos
   - WebP for better compression (with fallbacks)

2. Optimize images for web:
   - Compress appropriately
   - Use responsive images with srcset when needed
   - Lazy load images below the fold

3. Provide alt text for accessibility:
   ```html
   <img src="{% static 'app_name/img/logo.png' %}" alt="Company Logo">
   ```

## Loading Static Files

1. Use the Django `{% static %}` template tag:
   ```html
   {% load static %}
   <link rel="stylesheet" href="{% static 'app_name/css/template-name.css' %}">
   <script src="{% static 'app_name/js/template-name.js' %}"></script>
   ```

2. Use staticfiles versioning to prevent caching issues:
   ```html
   <link rel="stylesheet" href="{% static 'app_name/css/template-name.css' %}?v={{ version }}">
   ```

3. For template-specific static files, load them in the appropriate blocks:
   ```html
   {% block extra_css %}
     <link rel="stylesheet" href="{% static 'app_name/css/template-name.css' %}">
   {% endblock %}
   
   {% block extra_js %}
     <script src="{% static 'app_name/js/template-name.js' %}"></script>
   {% endblock %}
   ```

## Performance Considerations

1. Minify CSS and JavaScript files in production
2. Combine multiple CSS or JS files in production
3. Use deferred loading for non-critical JavaScript
4. Consider using a CDN for static files in production
5. Implement browser caching with appropriate headers