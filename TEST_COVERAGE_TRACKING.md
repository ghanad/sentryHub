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
|                   | `AlertGroup` (`models.py`)                |   🟢   | Creation, relations, default values, `__str__()`             |
|                   | `AlertInstance` (`models.py`)             |   🟢   | Creation, relations, `__str__()`                             |
|                   | `AlertComment` (`models.py`)              |   🟢   | Creation, relations, `__str__()`                             |
|                   | `AlertAcknowledgementHistory` (`models.py`) |   ⚪️   | Creation, relations, `__str__()`                             |
| **Forms**         |                                           |        |                                                              |
|                   | `SilenceRuleForm` (`forms.py`)            |   ⚪️   | Validation (JSON, dates, required), saving                  |
|                   | `AlertAcknowledgementForm` (`forms.py`)   |   ⚪️   | Validation (required comment)                                |
|                   | `AlertCommentForm` (`forms.py`)           |   ⚪️   | Validation, saving                                           |
| **Services**      |                                           |        |                                                              |
|                   | `check_alert_silence` (`silence_matcher.py`)|   ⚪️   | Matching logic (match/no match), DB updates (`is_silenced`) |
|                   | `process_alert` (`alerts_processor.py`)   |   ⚪️   | Firing/Resolved logic, instance creation/update, ack reset    |
|                   | `extract_alert_data` (`alerts_processor.py`)| ⚪️   | Data extraction logic, date parsing                          |
|                   | `get_or_create_alert_group` (`alerts_processor.py`)| ⚪️ | Create/Update logic                                      |
|                   | ... (other helpers in `alerts_processor.py`) | ⚪️   | Specific logic for firing/resolved                           |
|                   | `acknowledge_alert` (`alerts_processor.py`)|   ⚪️   | AlertGroup update, History creation                          |
|                   | `alert_logger.py`                         |   ⚫️   | File writing (might need integration test or mock `open`) |
| **Views**         |                                           |        |                                                              |
|                   | `AlertListView` (`views.py`)              |   ⚪️   | GET (status 200, template), filters, context, pagination    |
|                   | `AlertDetailView` (`views.py`)            |   ⚪️   | GET (status 200, template), context (tabs, forms), POST (ack, comment - valid/invalid), AJAX response |
|                   | `SilenceRuleListView` (`views.py`)        |   ⚪️   | GET, filters, context, pagination                           |
|                   | `SilenceRuleCreateView` (`views.py`)      |   ⚪️   | GET (initial data from query param), POST (valid/invalid), permissions, `check_alert_silence` call |
|                   | `SilenceRuleUpdateView` (`views.py`)      |   ⚪️   | GET, POST (valid/invalid), permissions, `check_alert_silence` call |
|                   | `SilenceRuleDeleteView` (`views.py`)      |   ⚪️   | GET (confirmation page), POST (deletion), permissions, `check_alert_silence` call |
|                   | `login_view` (`views.py`)                 |   ⚪️   | GET (show form), POST (valid/invalid login)                  |
| **API Views**     |                                           |        |                                                              |
|                   | `AlertWebhookView` (`api/views.py`)       |   ⚪️   | POST (valid/invalid serializer), calls `process_alert`, status codes |
|                   | `AlertGroupViewSet` (`api/views.py`)      |   ⚪️   | List/Retrieve (GET), filters, search, pagination, `acknowledge` action (PUT), `history` action (GET), `comments` action (GET/POST) |
|                   | `AlertHistoryViewSet` (`api/views.py`)    |   ⚪️   | List (GET), filters (fingerprint, dates)                     |
| **API Serializers**|                                          |        |                                                              |
|                   | `AlertmanagerWebhookSerializer` (`api/serializers.py`) | ⚪️ | Validation (required fields)                             |
|                   | `AcknowledgeAlertSerializer` (`api/serializers.py`) | ⚪️ | Validation                                                   |
|                   | ... (other serializers)                   |   ⚪️   | `SerializerMethodField` logic (if complex)                 |
| **Admin**         |                                           |        |                                                              |
|                   | `SilenceRuleAdmin` (`admin.py`)           |   ⚪️   | Custom methods (`display_matchers_short`, etc.), `save_model` |
|                   | ... (other ModelAdmins)                   |   ⚫️   | Basic registration checks (low priority)                     |

### `core` App

| Component            | File / Functionality                 | Status | Notes                                       |
| :------------------- | :----------------------------------- | :----: | :------------------------------------------ |
| **Views**            | `HomeView` (`views.py`)              |   ⚪️   | GET (check redirect)                        |
|                      | `AboutView` (`views.py`)             |   ⚪️   | GET (status 200, template)                  |
| **Middleware**       | `AdminAccessMiddleware` (`middleware.py`) |   ⚪️   | Staff/non-staff access, redirects           |
| **Context Processors**| `notifications` (`context_processors.py`) |   ⚪️   | Message extraction into context             |
| **Template Tags**    |                                      |        |                                             |
|                      | `core_tags.py`                       |   ⚪️   | `time_ago`, `status_badge`, `jsonify`, `format_datetime` filters |
|                      | `date_format_tags.py`                |   ⚪️   | `force_jalali`, `force_gregorian` filters (with timezone handling) |

### `docs` App

| Component         | File / Functionality                      | Status | Notes                                                        |
| :---------------- | :---------------------------------------- | :----: | :----------------------------------------------------------- |
| **Models**        | `AlertDocumentation` (`models.py`)        |   ⚪️   | Creation, relations, `__str__`                              |
|                   | `DocumentationAlertGroup` (`models.py`)   |   ⚪️   | Creation, relations, `unique_together`                       |
| **Forms**         | `AlertDocumentationForm` (`forms.py`)     |   ⚪️   | Validation, saving (TinyMCE might need specific handling) |
|                   | `DocumentationSearchForm` (`forms.py`)    |   ⚪️   | Basic validation (optional field)                            |
| **Services**      | `match_documentation_to_alert` (`documentation_matcher.py`) | ⚪️ | Matching logic (match/no match), Link creation          |
| **Views**         | `DocumentationListView` (`views.py`)      |   ⚪️   | GET, search, context, pagination                             |
|                   | `DocumentationDetailView` (`views.py`)    |   ⚪️   | GET, context (linked alerts)                                 |
|                   | `DocumentationCreateView` (`views.py`)    |   ⚪️   | GET, POST (valid/invalid), permissions                       |
|                   | `DocumentationUpdateView` (`views.py`)    |   ⚪️   | GET, POST (valid/invalid), permissions                       |
|                   | `DocumentationDeleteView` (`views.py`)    |   ⚪️   | GET, POST, permissions                                       |
|                   | `LinkDocumentationToAlertView` (`views.py`)|   ⚪️   | GET (context), POST (link creation/check existing)         |
|                   | `UnlinkDocumentationFromAlertView` (`views.py`)| ⚪️ | GET (not allowed), POST (deletion), AJAX response            |
| **API Views**     | `DocumentationViewSet` (`api/views.py`)   |   ⚪️   | CRUD (GET, POST, PUT, DELETE), search, filters, actions (link/unlink) |
|                   | `AlertDocumentationLinkViewSet` (`api/views.py`)| ⚪️ | List (GET), filters                                          |
| **Signals**       | `match_documentation_to_existing_alerts` (`signals.py`) | ⚪️ | Check if `match_documentation_to_alert` is called on save |
| **Admin**         | `AlertDocumentationAdmin` (`admin.py`)    |   ⚪️   | `save_model`, Inline checks (if needed)                      |

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
| **Signals**       | `create_user_profile`, `save_user_profile` (`signals.py`) | ⚪️ | Check if `UserProfile` exists after `User` save            |

### `admin_dashboard` App

| Component         | File / Functionality                      | Status | Notes                                                        |
| :---------------- | :---------------------------------------- | :----: | :----------------------------------------------------------- |
| **Views**         | `AdminDashboardView` (`views.py`)         |   ⚪️   | GET, permissions, context data aggregation                   |
|                   | `AdminCommentsView` (`views.py`)          |   ⚪️   | GET, permissions, filters, context, pagination             |
|                   | `AdminAcknowledgementsView` (`views.py`)  |   ⚪️   | GET, permissions, filters, context, pagination             |

### `main_dashboard` App

| Component         | File / Functionality                      | Status | Notes                                                        |
| :---------------- | :---------------------------------------- | :----: | :----------------------------------------------------------- |
| **Views**         | `DashboardView` (`views.py`)              |   ⚪️   | GET, context data aggregation (counts, queries)              |

### `tier1_dashboard` App

| Component         | File / Functionality                      | Status | Notes                                                        |
| :---------------- | :---------------------------------------- | :----: | :----------------------------------------------------------- |
| **Views**         | `Tier1DashboardView` (`views.py`)         |   ⚪️   | GET, queryset logic (filtering, ordering)                    |
| **API Views**     | `Tier1AlertDataAPIView` (`api/views.py`)  |   ⚪️   | GET, permissions, queryset logic, context for template render |

---

## Frontend Tests (JavaScript)

### `alerts` App JS

| File                | Functionality                               | Status | Notes                              |
| :------------------ | :------------------------------------------ | :----: | :--------------------------------- |
| `alert_detail.js`   | Duration calculation, Tab URL handling      |   ⚪️   | Unit test for `formatDuration`       |
| `comments.js`       | Form submit, char count, AJAX, Edit/Delete stubs, RTL |   ⚪️   | Integration tests (Testing Library) |
| `alert_history.js`  | Duration calculation                        |   ⚪️   | Unit test for `formatDuration`       |
| `notifications.js`  | Wrapper around Toastr                       |   ⚫️   | Low priority, simple wrapper      |

### `core` App JS

| File                | Functionality                               | Status | Notes                              |
| :------------------ | :------------------------------------------ | :----: | :--------------------------------- |
| `main.js`           | Tooltip/Popover init, alert closing         |   ⚫️   | Mostly Bootstrap init             |
| `notifications.js`  | `SentryNotification` object                 |   ⚫️   | Low priority, simple wrapper      |
| `rtl-text.js`       | `isPersianText`, `setTextDirection`, `handleInputDirection` | ⚪️ | Unit tests, DOM manipulation tests |

### `docs` App JS

| File                      | Functionality                               | Status | Notes                              |
| :------------------------ | :------------------------------------------ | :----: | :--------------------------------- |
| `documentation_detail.js` | `isPersianText`, `setTextDirection`         |   ⚪️   | Unit tests, DOM manipulation tests |

### `tier1_dashboard` App JS

| File                      | Functionality                               | Status | Notes                              |
| :------------------------ | :------------------------------------------ | :----: | :--------------------------------- |
| `tier1_dashboard.js`      | Auto-refresh `fetch`, Table update, Status update, Modal handling, Ack submit (`fetch`) | ⚪️ | Requires mocking `fetch`           |

### `users` App JS

| File                      | Functionality                               | Status | Notes                              |
| :------------------------ | :------------------------------------------ | :----: | :--------------------------------- |
| `preferences.js`          | (Currently empty)                           |   ⚫️   |                                    |
| `user_list.html` (JS in template) | Delete confirmation (`fetch`)         |   ⚪️   | Test via E2E or extract to JS file |
| `user_form.html` (JS in template) | AJAX form submit (`fetch`), error handling | ⚪️ | Test via E2E or extract to JS file |