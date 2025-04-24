# Prompt for AI Assistant: SentryHub Phase 3 - Dashboard Consolidation (Granular Tasks)

**Overall Goal:** Refactor the SentryHub Django project's dashboard structure by consolidating the `main_dashboard`, `tier1_dashboard`, and `admin_dashboard` apps into a single new `dashboard` app with role-based access control, while ensuring shared elements like the sidebar remain in the `core` app.

**Assumptions:**
* A shared site sidebar/navigation template exists within the `core` app (e.g., `core/templates/core/navbar.html`).

---

**Task 3.1: Create New Dashboard App Structure**

* **Objective:** Create the basic structure for the new consolidated dashboard app.
* **Instructions:**
    1.  Run the command: `python manage.py startapp dashboard`
    2.  Verify that the `dashboard/` directory is created with standard Django app files.

---

**Task 3.2: Move `main_dashboard` View**

* **Objective:** Move the primary view logic from `main_dashboard` to `dashboard`.
* **Instructions:**
    1.  Locate the main dashboard view (likely `ModernDashboardView` in `main_dashboard/views.py`).
    2.  Copy its definition to `dashboard/views.py`.
    3.  Add necessary standard Django imports to `dashboard/views.py` if missing. Do not fix cross-app imports yet.

---

**Task 3.3: Move `tier1_dashboard` View**

* **Objective:** Move the primary view logic from `tier1_dashboard` to `dashboard`.
* **Instructions:**
    1.  Locate the Tier 1 dashboard view (likely `UnackAlertsView` in `tier1_dashboard/views.py`).
    2.  Copy its definition to `dashboard/views.py`.

---

**Task 3.4: Move `admin_dashboard` View**

* **Objective:** Move the primary view logic from `admin_dashboard` to `dashboard`.
* **Instructions:**
    1.  Locate the Admin dashboard view (e.g., `AdminDashboardView` in `admin_dashboard/views.py`).
    2.  Copy its definition to `dashboard/views.py`.

---

**Task 3.5: Move `main_dashboard` Template**

* **Objective:** Move the main template file from `main_dashboard` to `dashboard`.
* **Instructions:**
    1.  Create directory structure `dashboard/templates/dashboard/`.
    2.  Locate the main template (likely `main_dashboard/templates/main_dashboard/dashboard.html`).
    3.  Move it to `dashboard/templates/dashboard/main_page.html`.
    4.  Update the corresponding view in `dashboard/views.py` to use `template_name = 'dashboard/main_page.html'` or render this path.

---

**Task 3.6: Move `tier1_dashboard` Template**

* **Objective:** Move the main template file from `tier1_dashboard` to `dashboard`.
* **Instructions:**
    1.  Locate the main template (likely `tier1_dashboard/templates/tier1_dashboard/unack_alerts.html`).
    2.  Move it to `dashboard/templates/dashboard/tier1_unacked.html`.
    3.  Update the corresponding view in `dashboard/views.py` to use `template_name = 'dashboard/tier1_unacked.html'` or render this path.

---

**Task 3.7: Move `admin_dashboard` Template**

* **Objective:** Move the main template file from `admin_dashboard` to `dashboard`.
* **Instructions:**
    1.  Locate the main template (likely `admin_dashboard/templates/admin_dashboard/dashboard.html`).
    2.  Move it to `dashboard/templates/dashboard/admin_summary.html`.
    3.  Update the corresponding view in `dashboard/views.py` to use `template_name = 'dashboard/admin_summary.html'` or render this path.

---

**Task 3.8: Consolidate Base Templates & Include Sidebar**

* **Objective:** Reduce duplication in dashboard templates and ensure the shared sidebar is included.
* **Instructions:**
    1.  Examine the templates moved into `dashboard/templates/dashboard/`.
    2.  Identify common HTML structure (headers, footers, main layout).
    3.  Create a base template (e.g., `dashboard/templates/dashboard/base.html`) containing this common structure.
    4.  **Crucially:** Ensure this new base template correctly includes the shared site sidebar/navigation template from the `core` app (e.g., using `{% include 'core/navbar.html' %}` or similar, verify the exact path in the `core` app). The sidebar template itself **must remain** in the `core` app.
    5.  Modify the specific dashboard templates (`main_page.html`, `tier1_unacked.html`, etc.) to `{% extend 'dashboard/base.html' %}` and use `{% block %}` tags for their unique content.

---

**Task 3.9: Refactor Templates for Conditional Display**

* **Objective:** Ensure templates show role-specific content correctly.
* **Instructions:**
    1.  Review the templates in `dashboard/templates/dashboard/`.
    2.  Use Django template tags (e.g., `{% if user.is_staff %}`, `{% if perms.some_app.some_perm %}`) and context variables passed from the views to conditionally display specific sections, data, or UI elements appropriate for the logged-in user's role.

---

**Task 3.10: Move Static Assets**

* **Objective:** Move dashboard-specific static files (CSS, JS).
* **Instructions:**
    1.  Create directories `dashboard/static/dashboard/css/` and `dashboard/static/dashboard/js/`.
    2.  Check the `static/` directories of the *old* apps (`main_dashboard`, `tier1_dashboard`, `admin_dashboard`).
    3.  Move any CSS/JS files *specific* to those dashboards into the new directories.
    4.  Update `{% static %}` tags in the moved templates (`dashboard/templates/dashboard/`) to reference the new paths (e.g., `{% static 'dashboard/css/specific.css' %}`).

---

**Task 3.11: Implement View Access Control**

* **Objective:** Add role-based access control to the moved views.
* **Instructions:**
    1.  Open `dashboard/views.py`.
    2.  Import necessary decorators/mixins (`login_required`, `user_passes_test`, `LoginRequiredMixin`, `UserPassesTestMixin`).
    3.  Apply `@login_required` (or `LoginRequiredMixin`) to all dashboard views.
    4.  For the Tier 1 view, add a test checking group membership or permissions (e.g., `user_passes_test(lambda u: u.groups.filter(name='Tier1').exists() or u.is_staff)`).
    5.  For the Admin view, add a test checking `is_staff` (e.g., `user_passes_test(lambda u: u.is_staff)`).
    6.  Adjust the tests as needed based on your specific permission model.

---

**Task 3.12: Configure `dashboard/urls.py`**

* **Objective:** Define URL patterns for the new `dashboard` app.
* **Instructions:**
    1.  Create `dashboard/urls.py`.
    2.  Import `path` and the views from `dashboard.views`.
    3.  Define `urlpatterns` mapping URL paths (e.g., `''`, `'tier1/'`, `'admin/'`) to the corresponding views.
    4.  Add `app_name = 'dashboard'`.

---

**Task 3.13: Update Main `urls.py`**

* **Objective:** Integrate new dashboard URLs and remove old ones.
* **Instructions:**
    1.  Edit the main project `urls.py`.
    2.  Remove `include()` lines for `main_dashboard`, `tier1_dashboard`, `admin_dashboard`.
    3.  Add `path('dashboard/', include('dashboard.urls'))` (adjust base path if needed).

---

**Task 3.14: Update `INSTALLED_APPS` Setting**

* **Objective:** Register the new app and unregister old ones.
* **Instructions:**
    1.  Edit `settings.py`.
    2.  Add `'dashboard'` to `INSTALLED_APPS`.
    3.  Remove `'main_dashboard'`, `'tier1_dashboard'`, `'admin_dashboard'` from `INSTALLED_APPS`.

---

**Task 3.15: Fix Imports in `dashboard` App**

* **Objective:** Correct import statements within the `dashboard` app code.
* **Instructions:**
    1.  Open `dashboard/views.py`. Review and fix all `import` statements referencing other project apps (`alerts`, `docs`, `users`, `core`, etc.).
    2.  Check `dashboard/urls.py` and any other Python files in the `dashboard` app for correct imports.

---

**Task 3.16: Update Cross-App References (Including Sidebar)**

* **Objective:** Find and fix references in *other* apps pointing to old dashboards.
* **Instructions:**
    1.  Search *outside* the `dashboard` app (in `alerts`, `docs`, `users`, `core`, etc.) for Python `import` statements referencing the old dashboard apps; remove or update them.
    2.  Search all template files (`*.html`) outside the `dashboard` app for `{% url %}` tags referencing old dashboard URL names; update them to use the new `dashboard:` namespace (e.g., `{% url 'dashboard:main' %}`) or remove if obsolete.
    3.  **Specifically check the shared sidebar template** (e.g., `core/templates/core/navbar.html`). Update any `{% url %}` tags inside it that pointed to old dashboards to use the new `dashboard:` URLs.

---

**Task 3.17: Run Migrations Check**

* **Objective:** Apply migrations and check for unexpected changes.
* **Instructions:**
    1.  Run `python manage.py makemigrations dashboard`. Expect "No changes detected".
    2.  Run `python manage.py migrate`.

---

**Task 3.18: Delete Old App Directories**

* **Objective:** Clean up the project structure.
* **Instructions:**
    1.  **Verify all necessary code and templates have been successfully moved and integrated.**
    2.  Delete the directories: `main_dashboard/`, `tier1_dashboard/`, and `admin_dashboard/`.

---

**Task 3.19: Update/Write Tests**

* **Objective:** Ensure tests cover the consolidated dashboard and access control.
* **Instructions:**
    1.  Move/update any relevant existing tests to `dashboard/tests.py`.
    2.  Write new tests in `dashboard/tests.py` focusing on role-based access (logging in as different users) and conditional template rendering.

---

**Task 3.20: Update Documentation**

* **Objective:** Reflect the changes in the project documentation.
* **Instructions:**
    1.  Open `CODEBASE_DOCUMENTATION.md`.
    2.  Remove sections for `main_dashboard`, `tier1_dashboard`, `admin_dashboard`.
    3.  Add/update the section for the `dashboard` app, explaining its unified role and role-based access.

---


**Note**
use this python to run command. 
```python
C:\codes\python_codes\prometheus_alerts\venv\Scripts\python.exe
```