# Prompt for AI Assistant: SentryHub Phase 3 - Dashboard Consolidation (Incremental Approach)

**Overall Goal:** Refactor the SentryHub Django project's dashboard structure incrementally by consolidating `main_dashboard`, `tier1_dashboard`, and `admin_dashboard` apps into a single new `dashboard` app, one dashboard at a time.

**Assumptions:**
* Phase 1 (Integration/Notification app creation & signals) is complete.
* Phase 2 (Alert processor refactoring) is complete.
* A shared site sidebar/navigation template exists within the `core` app (e.g., `core/templates/core/navbar.html`).

---
**Part A: Setup New Dashboard App**
---

**Task 3.A.1: Create New Dashboard App Structure**
* **Objective:** Create the basic structure for the new consolidated dashboard app.
* **Instructions:**
    1.  Run the command: `python manage.py startapp dashboard`
    2.  Create necessary subdirectories:
        * `dashboard/templates/dashboard/`
        * `dashboard/static/dashboard/css/`
        * `dashboard/static/dashboard/js/`
    3.  Create an empty `dashboard/urls.py` file.
    4.  Add `'dashboard'` to the `INSTALLED_APPS` list in `settings.py`.

---
**Part B: Migrate `main_dashboard`**
---

**Task 3.B.1: Move `main_dashboard` View**
* **Objective:** Move the primary view from `main_dashboard` to `dashboard`.
* **Instructions:**
    1.  Locate the main dashboard view (likely `ModernDashboardView` in `main_dashboard/views.py`).
    2.  Copy its *entire* definition (including its own imports) to `dashboard/views.py`.
    3.  Add standard Django imports if missing at the top of `dashboard/views.py`.

**Task 3.B.2: Move `main_dashboard` Template**
* **Objective:** Move the main template file from `main_dashboard` to `dashboard`.
* **Instructions:**
    1.  Locate the main template (likely `main_dashboard/templates/main_dashboard/dashboard.html`).
    2.  Move it to `dashboard/templates/dashboard/main_page.html`.
    3.  Update the view moved in Task 3.B.1 (`dashboard/views.py`) to use `template_name = 'dashboard/main_page.html'` or render this path.

**Task 3.B.3: Move `main_dashboard` Static Assets**
* **Objective:** Move static files specific to `main_dashboard`.
* **Instructions:**
    1.  Check `main_dashboard/static/main_dashboard/`.
    2.  Move any *specific* CSS/JS files to `dashboard/static/dashboard/css/` or `dashboard/static/dashboard/js/`.
    3.  Update `{% static %}` tags in `dashboard/templates/dashboard/main_page.html` to use the new paths (e.g., `{% static 'dashboard/css/main_dashboard.css' %}`).

**Task 3.B.4: Configure URL for `main_dashboard` View**
* **Objective:** Create a URL pattern for the moved view within the `dashboard` app.
* **Instructions:**
    1.  Open `dashboard/urls.py`.
    2.  Import `path` and the specific view moved in Task 3.B.1 (e.g., `from .views import ModernDashboardView`).
    3.  Define `urlpatterns` and add a pattern for this view. Assign a unique name. Add `app_name = 'dashboard'`.
        ```python
        # dashboard/urls.py
        from django.urls import path
        from . import views # Or import specific view

        app_name = 'dashboard'

        urlpatterns = [
            path('main/', views.ModernDashboardView.as_view(), name='main_dashboard_new'), # Example
        ]
        ```
    4.  Open the main project `urls.py`. Add an include for the `dashboard` app *if it doesn't exist yet*: `path('dashboard/', include('dashboard.urls'))`. Remove the *old* include for `main_dashboard.urls`.

**Task 3.B.5: Fix Imports for Moved `main_dashboard` View**
* **Objective:** Correct imports within the view moved to `dashboard/views.py`.
* **Instructions:**
    1.  Open `dashboard/views.py`.
    2.  Focus *only* on the view moved from `main_dashboard`.
    3.  Review its import statements. Correct any imports referencing other project apps (`alerts`, `core`, `users`, etc.) to use the proper paths.

**Task 3.B.6: Update References to `main_dashboard`**
* **Objective:** Find and update references pointing to the *old* `main_dashboard`.
* **Instructions:**
    1.  Search the *entire codebase* (including `core/templates/core/navbar.html`) for `{% url %}` tags referencing URL names from the *old* `main_dashboard.urls`. Update them to use the new name defined in `dashboard.urls` (e.g., `{% url 'dashboard:main_dashboard_new' %}`).
    2.  Search the codebase for Python imports like `from main_dashboard...`. Remove or update them if they are no longer needed or should point elsewhere.

**Task 3.B.7: Test `main_dashboard` Migration**
* **Objective:** Verify the migrated dashboard works correctly.
* **Instructions:**
    1.  Run the development server.
    2.  Navigate to the new URL for the main dashboard (e.g., `/dashboard/main/`).
    3.  Verify it renders correctly, static files load, and links work.
    4.  Run relevant tests if you have them. Fix any errors specifically related to this migration step.

---
**Part C: Migrate `tier1_dashboard`**
---

**Task 3.C.1: Move `tier1_dashboard` View**
* **Objective:** Move the primary view from `tier1_dashboard` to `dashboard`.
* **Instructions:**
    1.  Locate the Tier 1 view (likely `UnackAlertsView` in `tier1_dashboard/views.py`).
    2.  Copy its definition to `dashboard/views.py`.

**Task 3.C.2: Move `tier1_dashboard` Template**
* **Objective:** Move the main template file from `tier1_dashboard` to `dashboard`.
* **Instructions:**
    1.  Locate the Tier 1 template (likely `tier1_dashboard/templates/tier1_dashboard/unack_alerts.html`).
    2.  Move it to `dashboard/templates/dashboard/tier1_unacked.html`.
    3.  Update the view moved in Task 3.C.1 (`dashboard/views.py`) to use `template_name = 'dashboard/tier1_unacked.html'`.

**Task 3.C.3: Move `tier1_dashboard` Static Assets**
* **Objective:** Move static files specific to `tier1_dashboard`.
* **Instructions:**
    1.  Check `tier1_dashboard/static/tier1_dashboard/`.
    2.  Move any *specific* CSS/JS files to `dashboard/static/dashboard/`.
    3.  Update `{% static %}` tags in `dashboard/templates/dashboard/tier1_unacked.html`.

**Task 3.C.4: Configure URL for `tier1_dashboard` View**
* **Objective:** Add a URL pattern for the moved Tier 1 view.
* **Instructions:**
    1.  Open `dashboard/urls.py`.
    2.  Import the Tier 1 view.
    3.  Add a path to `urlpatterns` (e.g., `path('tier1/', views.UnackAlertsView.as_view(), name='tier1_dashboard_new')`).
    4.  Open the main project `urls.py`. Remove the *old* include for `tier1_dashboard.urls`.

**Task 3.C.5: Fix Imports for Moved `tier1_dashboard` View**
* **Objective:** Correct imports within the Tier 1 view in `dashboard/views.py`.
* **Instructions:**
    1.  Open `dashboard/views.py`.
    2.  Focus *only* on the view moved from `tier1_dashboard`.
    3.  Review and correct its import statements referencing other project apps.

**Task 3.C.6: Update References to `tier1_dashboard`**
* **Objective:** Find and update references pointing to the *old* `tier1_dashboard`.
* **Instructions:**
    1.  Search the codebase (including sidebar) for `{% url %}` tags referencing old `tier1_dashboard` URL names. Update them to use the new name (e.g., `{% url 'dashboard:tier1_dashboard_new' %}`).
    2.  Search for Python imports like `from tier1_dashboard...`. Remove or update.

**Task 3.C.7: Test `tier1_dashboard` Migration**
* **Objective:** Verify the migrated Tier 1 dashboard works.
* **Instructions:**
    1.  Run the server.
    2.  Navigate to the new URL (e.g., `/dashboard/tier1/`).
    3.  Verify rendering, static files, and functionality. Test with appropriate user roles.
    4.  Run/fix relevant tests.

---
**Part D: Migrate `admin_dashboard`**
---

**Task 3.D.1: Move `admin_dashboard` View**
* **Objective:** Move the primary view from `admin_dashboard` to `dashboard`.
* **Instructions:**
    1.  Locate the Admin view (e.g., `AdminDashboardView` in `admin_dashboard/views.py`).
    2.  Copy its definition to `dashboard/views.py`.

**Task 3.D.2: Move `admin_dashboard` Template**
* **Objective:** Move the main template file from `admin_dashboard` to `dashboard`.
* **Instructions:**
    1.  Locate the Admin template (likely `admin_dashboard/templates/admin_dashboard/dashboard.html`).
    2.  Move it to `dashboard/templates/dashboard/admin_summary.html`.
    3.  Update the view moved in Task 3.D.1 (`dashboard/views.py`) to use `template_name = 'dashboard/admin_summary.html'`.

**Task 3.D.3: Move `admin_dashboard` Static Assets**
* **Objective:** Move static files specific to `admin_dashboard`.
* **Instructions:**
    1.  Check `admin_dashboard/static/admin_dashboard/`.
    2.  Move any *specific* CSS/JS files to `dashboard/static/dashboard/`.
    3.  Update `{% static %}` tags in `dashboard/templates/dashboard/admin_summary.html`.

**Task 3.D.4: Configure URL for `admin_dashboard` View**
* **Objective:** Add a URL pattern for the moved Admin view.
* **Instructions:**
    1.  Open `dashboard/urls.py`.
    2.  Import the Admin view.
    3.  Add a path to `urlpatterns` (e.g., `path('admin-summary/', views.AdminDashboardView.as_view(), name='admin_dashboard_new')`).
    4.  Open the main project `urls.py`. Remove the *old* include for `admin_dashboard.urls`.

**Task 3.D.5: Fix Imports for Moved `admin_dashboard` View**
* **Objective:** Correct imports within the Admin view in `dashboard/views.py`.
* **Instructions:**
    1.  Open `dashboard/views.py`.
    2.  Focus *only* on the view moved from `admin_dashboard`.
    3.  Review and correct its import statements.

**Task 3.D.6: Update References to `admin_dashboard`**
* **Objective:** Find and update references pointing to the *old* `admin_dashboard`.
* **Instructions:**
    1.  Search the codebase (including sidebar) for `{% url %}` tags referencing old `admin_dashboard` URL names. Update them to use the new name (e.g., `{% url 'dashboard:admin_dashboard_new' %}`).
    2.  Search for Python imports like `from admin_dashboard...`. Remove or update.

**Task 3.D.7: Test `admin_dashboard` Migration**
* **Objective:** Verify the migrated Admin dashboard works.
* **Instructions:**
    1.  Run the server.
    2.  Navigate to the new URL (e.g., `/dashboard/admin-summary/`).
    3.  Verify rendering, static files, and functionality. Test as a staff user.
    4.  Run/fix relevant tests.

---
**Part E: Consolidation and Cleanup**
---

**Task 3.E.1: Consolidate Base Templates & Include Sidebar**
* **Objective:** Create a shared base template for all dashboards in the `dashboard` app.
* **Instructions:**
    1.  Examine `main_page.html`, `tier1_unacked.html`, `admin_summary.html` in `dashboard/templates/dashboard/`.
    2.  Create `dashboard/templates/dashboard/base.html` with common structure (HTML head, body tags, potentially including the `core` sidebar: `{% include 'core/navbar.html' %}`).
    3.  Modify the specific dashboard templates to `{% extend 'dashboard/base.html' %}` and use `{% block %}` tags.

**Task 3.E.2: Implement Access Control in Views**
* **Objective:** Apply consistent role-based access control.
* **Instructions:**
    1.  Open `dashboard/views.py`.
    2.  Import necessary decorators/mixins (`login_required`, `user_passes_test`, etc.).
    3.  Ensure *all* views require login (`@login_required` or `LoginRequiredMixin`).
    4.  Apply `user_passes_test` or `UserPassesTestMixin` to restrict the Tier 1 view (e.g., `lambda u: u.groups.filter(name='Tier1').exists() or u.is_staff`) and the Admin view (e.g., `lambda u: u.is_staff`).

**Task 3.E.3: Refactor Templates for Conditional Display**
* **Objective:** Use template tags for role-specific content.
* **Instructions:**
    1.  Review templates in `dashboard/templates/dashboard/`.
    2.  Use `{% if user.is_staff %}`, `{% if user|has_group:"Tier1" %}` (requires a custom template tag/filter `has_group`), etc., to show/hide elements based on role.

**Task 3.E.4: Final URL Configuration (Optional Refinement)**
* **Objective:** Refine the URL structure if desired.
* **Instructions:**
    1.  Review `dashboard/urls.py` and the main `urls.py` include.
    2.  Adjust the base path (e.g., `/dashboard/`) or individual paths (`main/`, `tier1/`, etc.) if a cleaner structure is desired now that all are consolidated. Ensure `name=` values are consistent and used correctly in `{% url %}` tags.

**Task 3.E.5: Delete Old App Directories**
* **Objective:** Remove obsolete code.
* **Instructions:**
    1.  **Verify all migrations (Parts B, C, D) were successful and tested.**
    2.  Delete the directories: `main_dashboard/`, `tier1_dashboard/`, `admin_dashboard/`.

**Task 3.E.6: Remove Old Apps from `INSTALLED_APPS`**
* **Objective:** Clean up settings.
* **Instructions:**
    1.  Edit `settings.py`.
    2.  Remove the entries `'main_dashboard'`, `'tier1_dashboard'`, `'admin_dashboard'` from the `INSTALLED_APPS` list.

**Task 3.E.7: Run Final Migrations Check**
* **Objective:** Catch any remaining migration issues.
* **Instructions:**
    1.  Run `python manage.py makemigrations`. Expect "No changes detected".
    2.  Run `python manage.py migrate`.

**Task 3.E.8: Update/Write Comprehensive Tests**
* **Objective:** Ensure full test coverage for the consolidated dashboard.
* **Instructions:**
    1.  Consolidate/update relevant old tests into `dashboard/tests.py`.
    2.  Write comprehensive tests covering all views, role-based access scenarios, and conditional rendering in `dashboard/tests.py`.

**Task 3.E.9: Update Documentation**
* **Objective:** Reflect the final structure in documentation.
* **Instructions:**
    1.  Open `CODEBASE_DOCUMENTATION.md`.
    2.  Ensure descriptions for the old dashboard apps are removed.
    3.  Update the description for the `dashboard` app, explaining its unified role, key views, and role-based access.

---
