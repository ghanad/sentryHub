# SentryHub Test Coverage Tracking

This document tracks the testing progress for different parts of the SentryHub application.

**Status Legend:**
*   ⚪️ Not Started
*   🟡 In Progress
*   🟢 Done
*   ⚫️ Not Applicable / Low Priority

---

## Backend Tests (Django/Python)

### `alerts` App

| Component         | File / Functionality                      | Status | Notes                                                        |
| :---------------- | :---------------------------------------- | :----: | :----------------------------------------------------------- |
| **Models**        |                                           |        |                                                              |
|                   | `SilenceRule` (`models.py`)               |   🟢   | Basic creation, `is_active()`, `__str__()`                    |
|                   | `AlertGroup` (`models.py`)                |   🟢   | Creation, relations, defaults, `__str__`, ordering           |
|                   | `AlertInstance` (`models.py`)             |   🟢   | Creation, relations, `__str__`, ordering                     |
|                   | `AlertComment` (`models.py`)              |   🟢   | Creation, relations, `__str__`, ordering                     |
|                   | `AlertAcknowledgementHistory` (`models.py`) |   🟢   | Creation, relations, `__str__`, ordering, FK behavior      |
|                   | `JiraIntegrationRule` (`models.py`)       |   🟢   | Creation, validation (`clean`), `__str__`, `get_assignee`   |
| **Forms**         |                                           |        |                                                              |
|                   | `SilenceRuleForm` (`forms.py`)            |   🟢   | Validation (JSON, dates, required), clean methods, saving     |
|                   | `AlertAcknowledgementForm` (`forms.py`)   |   🟢   | Validation (required comment)                                |
|                   | `AlertCommentForm` (`forms.py`)           |   🟢   | Validation (required), saving (commit=False), widget attrs   |
| **Services**      |                                           |        |                                                              |
|                   | `check_alert_silence` (`silence_matcher.py`)|   🟢   | Matching logic, DB updates, multiple rules, expiry         |
|                   | `acknowledge_alert` (`alerts_processor.py`)|   🟢   | AlertGroup update, History creation                          |
|                   | `get_active_firing_instance` (`alerts_processor.py`) | 🟢 | Logic for finding active instance                        |
|                   | `update_alert_state` (`alert_state_manager.py`) | 🟢 | Main logic for group/instance creation/update, status transitions |
|                   | `parse_alertmanager_payload` (`payload_parser.py`) | 🟢 | Parsing different payload versions, date handling, missing fields |
|                   | `jira_service.py`                         |   🟢   | (Also in integrations) API calls, connection handling         |
|                   | `jira_matcher.py`                         |   🟢   | (Also in integrations) Rule matching logic                   |
|                   | `alert_logger.py`                         |   ⚫️   | File writing (might need integration test or mock `open`) |
| **Views**         |                                           |        |                                                              |
|                   | `AlertListView` (`views.py`)              |   🟢   | GET (status, template), filters, context, pagination        |
|                   | `AlertDetailView` (`views.py`)            |   🟢   | GET (status, template), context, POST (ack, comment), AJAX  |
|                   | `acknowledge_alert_from_list` (`views.py`)|   🟢   | POST handling, form validation, messages, redirects        |
|                   | `SilenceRuleListView` (`views.py`)        |   🟢   | GET (auth, status, template), filters, context, pagination |
|                   | `SilenceRuleCreateView` (`views.py`)      |   🟢   | GET (auth, initial data), POST (valid/invalid form), service calls |
|                   | `SilenceRuleUpdateView` (`views.py`)      |   🟢   | GET, POST (valid/invalid), permissions, service calls      |
|                   | `SilenceRuleDeleteView` (`views.py`)      |   🟢   | GET (confirmation), POST (deletion), permissions, service calls |
|                   | `login_view` (`views.py`)                 |   🟢   | Basic GET/POST handling, authentication, redirects           |
| **API Views**     |                                           |        |                                                              |
|                   | `AlertWebhookView` (`api/views.py`)       |   🟢   | POST (valid/invalid serializer), calls task, status codes    |
|                   | `AlertGroupViewSet` (`api/views.py`)      |   🟢   | List/Retrieve (GET), filters, actions (ack, history, comments) |
|                   | `AlertHistoryViewSet` (`api/views.py`)    |   🟢   | List (GET), filters (status, fingerprint, start_date, end_date) |
| **API Serializers**|                                          |        |                                                              |
|                   | `AlertInstanceSerializer` (`api/serializers.py`) | 🟢 | Serialization structure                                      |
|                   | `AlertAcknowledgementHistorySerializer` (`api/serializers.py`) | 🟢 | Serialization, MethodFields                        |
|                   | `AlertGroupSerializer` (`api/serializers.py`) | 🟢 | Serialization, MethodFields                        |
|                   | `AlertCommentSerializer` (`api/serializers.py`) | 🟢 | Serialization, MethodFields                        |
|                   | `AlertmanagerWebhookSerializer` (`api/serializers.py`) | 🟢 | Validation (required fields)                             |
|                   | `AcknowledgeAlertSerializer` (`api/serializers.py`) | 🟢 | Validation                                                   |
| **Admin**         |                                           |        |                                                              |
|                   | `AlertGroupAdmin` (`admin.py`)            |   🟢   | `jira_issue_key_link` method                              |
|                   | `AlertInstanceAdmin` (`admin.py`)         |   ⚫️   | Basic registration checks                                    |
|                   | `AlertCommentAdmin` (`admin.py`)          |   ⚫️   | Basic registration checks                                    |
|                   | `AlertAcknowledgementHistoryAdmin` (`admin.py`) | ⚫️ | Basic registration checks                                    |
|                   | `SilenceRuleAdmin` (`admin.py`)           |   🟢   | Custom methods, `save_model`                               |
                  | `JiraRuleMatcherAdmin` (`admin.py`)       |   ⚪️   | Custom methods (`get_criteria_preview`)                     |
| **Signals**       | `signals.py`                              |   ⚪️   | Test `handle_silence_rule_save/delete` trigger `_rescan_alerts_for_silence` |
| **Handlers**      | `handlers.py`                             |   ⚪️   | Test `handle_silence_check` receiver logic                 |
| **Tasks**         | `process_alert_payload_task` (`tasks.py`) |   ⚪️   | Task logic, exception handling, signal sending             |

### `core` App

| Component            | File / Functionality                 | Status | Notes                                       |
| :------------------- | :----------------------------------- | :----: | :------------------------------------------ |
| **Models**           | `models.py`                          |   ⚫️   | Empty file                                  |
| **Views**            | `HomeView` (`views.py`)              |   ⚪️   | GET (check redirect)                        |
|                      | `AboutView` (`views.py`)             |   ⚪️   | GET (status 200, template)                  |
| **Middleware**       | `AdminAccessMiddleware` (`middleware.py`) |   ⚪️   | Staff/non-staff access, redirects           |
| **Context Processors**| `notifications` (`context_processors.py`) |   ⚪️   | Message extraction into context             |
| **Template Tags**    |                                      |        |                                             |
|                      | `core_tags.py`                       |   ⚪️   | `time_ago`, `status_badge`, `jsonify`, `format_datetime`, `has_group`, `calculate_duration` |
|                      | `date_format_tags.py`                |   ⚪️   | `to_jalali`, `to_jalali_datetime`, `force_jalali`, `force_gregorian` |
|                      | `add_class` (`core_tags.py`)                 |   ⚪️   | Adds CSS classes to form fields                      |

### `docs` App

| Component         | File / Functionality                      | Status | Notes                                                        |
| :---------------- | :---------------------------------------- | :----: | :----------------------------------------------------------- |
| **Models**        | `AlertDocumentation` (`models.py`)        |   ⚪️   | Creation, relations, `__str__`                              |
|                   | `DocumentationAlertGroup` (`models.py`)   |   ⚪️   | Creation, relations, `unique_together`                       |
| **Forms**         | `AlertDocumentationForm` (`forms.py`)     |   ⚪️   | Validation, saving (TinyMCE might need specific handling) |
|                   | `DocumentationSearchForm` (`forms.py`)    |   ⚪️   | Basic validation (optional field)                            |
| **Services**      | `match_documentation_to_alert` (`documentation_matcher.py`) | ⚪️ | Matching logic (match/no match), Link creation          |
|                   | `get_documentation_for_alert` (`documentation_matcher.py`) | ⚪️ | Query logic                                                |
| **Views**         | `DocumentationListView` (`views.py`)      |   ⚪️   | GET, search, context, pagination                             |
|                   | `DocumentationDetailView` (`views.py`)    |   ⚪️   | GET, context (linked alerts)                                 |
|                   | `DocumentationCreateView` (`views.py`)    |   ⚪️   | GET (initial), POST (valid/invalid), permissions                       |
|                   | `DocumentationUpdateView` (`views.py`)    |   ⚪️   | GET, POST (valid/invalid), permissions                       |
|                   | `DocumentationDeleteView` (`views.py`)    |   ⚪️   | GET, POST, permissions                                       |
|                   | `LinkDocumentationToAlertView` (`views.py`)|   ⚪️   | GET (context), POST (link creation/check existing)         |
|                   | `UnlinkDocumentationFromAlertView` (`views.py`)| ⚪️ | POST (deletion), AJAX response                               |
| **API Views**     | `DocumentationViewSet` (`api/views.py`)   |   ⚪️   | CRUD, search, filters, actions (link/unlink)               |
|                   | `AlertDocumentationLinkViewSet` (`api/views.py`)| ⚪️ | List (GET), filters                                          |
| **API Serializers**| `AlertDocumentationSerializer` (`api/serializers.py`) | ⚪️ | Serialization, MethodFields                        |
|                   | `DocumentationAlertGroupSerializer` (`api/serializers.py`) | ⚪️ | Serialization, MethodFields                        |
| **Signals**       | `handle_documentation_save` (`signals.py`)|   ⚪️   | Check if `match_documentation_to_alert` is called logic on save |
| **Handlers**      | `handle_documentation_matching` (`handlers.py`) | ⚪️ | Test receiver logic for `match_documentation_to_alert` call |
| **Admin**         | `AlertDocumentationAdmin` (`admin.py`)    |   ⚪️   | `save_model`, Inline checks (if needed)                      |
|                   | `DocumentationAlertGroupAdmin` (`admin.py`) | ⚫️   | Basic registration checks                                    |
|                   | `DocumentationAlertGroupInline` (`admin.py`) |   ⚪️   | Basic inline registration checks                     |

### `users` App

| Component         | File / Functionality                      | Status | Notes                                                        |
| :---------------- | :---------------------------------------- | :----: | :----------------------------------------------------------- |
| **Models**        | `UserProfile` (`models.py`)               |   ⚪️   | Creation, relations, default values, choices                 |
| **Forms**         | `CustomUserCreationForm` (`forms.py`)     |   ⚪️   | Validation (email, passwords), saving user & profile         |
|                   | `CustomUserChangeForm` (`forms.py`)       |   ⚪️   | Validation (optional password), saving user & profile update |
| **Views**         | `UserListView` (`views.py`)               |   ⚪️   | GET, permissions, search, pagination                         |
|                   | `UserCreateView` (`views.py`)             |   ⚪️   | GET, POST (valid/invalid), permissions, AJAX handling        |
|                   | `UserUpdateView` (`views.py`)             |   ⚪️   | GET, POST (valid/invalid), permissions, AJAX handling        |
|                   | `UserDeleteView` (`views.py`)             |   ⚪️   | GET, POST, permissions, AJAX handling                        |
|                   | `UserProfileView` (`views.py`)            |   ⚪️   | GET, context                                                 |
|                   | `PreferencesView` (`views.py`)            |   ⚪️   | GET, context                                                 |
|                   | `update_preferences` (`views.py`)         |   ⚪️   | POST (valid/invalid data), profile update                    |
|                   | `AdminRequiredMixin` (`views.py`)            |   ⚪️   | Permission mixin for admin access                      |
| **Signals**       | `create_user_profile`, `save_user_profile` (`signals.py`) | ⚪️ | Check if `UserProfile` exists after `User` save            |
| **Admin**         | `admin.py`                                |   ⚫️   | Empty file                                                   |

### `dashboard` App

| Component         | File / Functionality                      | Status | Notes                                                        |
| :---------------- | :---------------------------------------- | :----: | :----------------------------------------------------------- |
| **Models**        | `models.py`                               |   ⚫️   | Empty file                                                   |
| **Views**         | `DashboardView` (`views.py`)              |   ⚪️   | GET, context data aggregation (counts, queries, charts)     |
|                   | `Tier1AlertListView` (`views.py`)         |   ⚪️   | GET, queryset logic (unacked filter), permissions          |
|                   | `AdminDashboardView` (`views.py`)         |   ⚪️   | GET, permissions, context data aggregation                   |
|                   | `AdminCommentsView` (`views.py`)          |   ⚪️   | GET, permissions, filters, context, pagination             |
|                   | `AdminAcknowledgementsView` (`views.py`)  |   ⚪️   | GET, permissions, filters, context, pagination             |
| **Admin**         | `admin.py`                                |   ⚫️   | Empty file                                                   |

### `integrations` App

| Component         | File / Functionality                      | Status | Notes                                                        |
| :---------------- | :---------------------------------------- | :----: | :----------------------------------------------------------- |
| **Models**        | `JiraIntegrationRule` (`models.py`)       |   ⚪️   | Creation, relations, `__str__`, ordering                   |
| **Forms**         | `JiraIntegrationRuleForm` (`forms.py`)    |   ⚪️   | Validation, saving, queryset for matchers                  |
| **Services**      | `JiraService` (`jira_service.py`)         |   ⚪️   | `__init__`, `check_connection`, `create_issue`, `add_comment`, `get_issue_status_category`, `add_watcher` |
|                   | `JiraRuleMatcherService` (`jira_matcher.py`) | ⚪️ | `find_matching_rule`, `_does_rule_match`, `_does_criteria_match` |
| **Views**         | `JiraRuleListView` (`views.py`)           |   ⚪️   | GET, filters, context, pagination                            |
|                   | `JiraRuleCreateView` (`views.py`)         |   ⚪️   | GET, POST (valid/invalid), permissions                       |
|                   | `JiraRuleUpdateView` (`views.py`)         |   ⚪️   | GET, POST (valid/invalid), permissions                       |
|                   | `JiraRuleDeleteView` (`views.py`)         |   ⚪️   | GET, POST, permissions, check for referenced alerts        |
|                   | `jira_admin_view` (`views.py`)            |   ⚪️   | Connection testing, test issue creation                      |
|                   | `jira_rule_guide_view` (`views.py`)       |   ⚪️   | Display markdown guide content                             |
| **Handlers**      | `handle_alert_processed` (`handlers.py`)  |   ⚪️   | Receiver logic, conditions (status, silence), task call     |
| **Tasks**         | `process_jira_for_alert_group` (`tasks.py`)|   ⚪️   | Task logic, error handling, retry logic, API calls         |
                  | `JiraTaskBase` (`tasks.py`)               |   ⚪️   | Base class for Jira tasks with retry logic                   |
                  | `render_template_safe` (`tasks.py`)       |   ⚪️   | Helper function for safe template rendering                  |
| **Admin**         | `JiraIntegrationRuleAdmin` (`admin.py`)   |   ⚪️   | Custom methods (`matcher_count`), fieldsets                |

---

## Frontend Tests (JavaScript)

### `alerts` App JS

| File                  | Functionality                               | Status | Notes                              |
| :-------------------- | :------------------------------------------ | :----: | :--------------------------------- |
| `alert_detail.js`     | Duration calculation, Tab URL handling      |   ⚪️   | Unit test for `formatDuration`       |
| `comments.js`         | Form submit, char count, AJAX, Edit/Delete stubs, RTL |   ⚪️   | Integration tests (Testing Library) |
| `alert_history.js`    | Duration calculation                        |   ⚪️   | Unit test for `formatDuration`       |
| `notifications.js`    | Wrapper around Toastr                       |   ⚫️   | Low priority, simple wrapper      |
| `silence_rule_list.js`| Tooltip init, potentially delete confirmation |   ⚪️   | Basic DOM/event tests              |

### `core` App JS

| File                | Functionality                               | Status | Notes                              |
| :------------------ | :------------------------------------------ | :----: | :--------------------------------- |
| `main.js`           | Tooltip/Popover init, Auto-hide alerts, Confirm delete, Toggle sidebar, Periodic data refresh, AJAX form submission |   ⚪️   |                                    |
| `notifications.js`  | `SentryNotification` object                 |   ⚫️   | Low priority, simple wrapper      |
| `rtl-text.js`       | `isPersianText`, `setTextDirection`, `handleInputDirection` | ⚪️ | Unit tests, DOM manipulation tests |

### `docs` App JS

| File                           | Functionality                               | Status | Notes                              |
| :----------------------------- | :------------------------------------------ | :----: | :--------------------------------- |
| `documentation_list.js`        | Tooltip init, potentially delete confirmation |   ⚪️   | Basic DOM/event tests              |
| `documentation_detail.js`      | Tooltip init, RTL detection, unlink confirm |   ⚪️   | Unit tests, DOM tests              |
| `documentation_confirm_delete.js`| Tooltip init (if any)                       |   ⚪️   | Basic DOM tests                    |
| `documentation_form.js`        | Tooltip init, potential TinyMCE interaction |   ⚪️   | Basic DOM tests                    |

### `dashboard` App JS

| File                   | Functionality                               | Status | Notes                              |
| :--------------------- | :------------------------------------------ | :----: | :--------------------------------- |
| `modern_dashboard.js`  | Sidebar toggle/pin, Mobile sidebar toggle, Collapsed account menu toggle, Account dropdown toggle, Apply initial sidebar state, Modified hover behavior, Theme toggle, DateTime update, Tooltips | ⚪️ | DOM manipulation, localStorage tests |
| `unack_alerts.js`      | Auto-refresh `fetch`, Update table, Detect new alerts, Play notification sound, Update alert count, Countdown timer, Initialize dynamic content (tooltips, event listeners), Handle row clicks, Handle expand/collapse | ⚪️ | Requires mocking `fetch`, timers, DOM manipulation tests |
| `admin.js`             | Tooltip init, Date range logic, Delete confirm stub, Toggle sidebar on mobile, Admin notification system, Handle bulk actions | ⚪️ | Basic DOM/event tests              |

### `users` App JS

| File                | Functionality                               | Status | Notes                              |
| :------------------ | :------------------------------------------ | :----: | :--------------------------------- |
| `preferences.js`    | (Currently empty)                           |   ⚫️   |                                    |
| `user_list.html` (JS)| Delete confirmation (`fetch`), Modal handling | ⚪️ | Test via E2E or extract to JS file |
| `user_form.html` (JS)| AJAX form submit (`fetch`), error handling | ⚪️ | Test via E2E or extract to JS file |