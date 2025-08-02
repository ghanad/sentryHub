# SentryHub Project Overview for AI Assistants (LLM)

**Last Updated:** [Insert Date Here]

## 1. Introduction and Project Goal

**SentryHub** is a **Django**-based web application developed to **receive, process, manage, and enrich alerts** sent from **Prometheus Alertmanager**. The primary goal is to create a powerful central dashboard for Operations teams and System Administrators to quickly view, analyze, prioritize, and manage alerts, thereby reducing response times to issues.

## 2. Key Features

*   **Alert Reception:** Receives alerts via a dedicated **Webhook API** (`alerts/api/webhook/`).
*   **Asynchronous Processing:** Utilizes **Celery** and **Redis** for background processing of alert payloads, preventing blocking of incoming requests.
*   **Alert Grouping & Management:**
    *   Creates `AlertGroup` based on the alert's `fingerprint`.
    *   Records history (`AlertInstance`) for each `firing` or `resolved` status update.
    *   Displays current status (`firing`/`resolved`), severity, labels, annotations, and first/last occurrence times.
*   **Silence Rules:**
    *   Allows defining rules to temporarily mute alerts based on their labels.
    *   Automatically checks active alerts against silence rules.
*   **Acknowledgement & Comments:**
    *   Users can acknowledge alerts.
    *   Acknowledgement history is recorded with comments.
    *   Separate comments can be added to each `AlertGroup`.
*   **Documentation Integration:**
    *   Ability to create internal documentation for different alert types (e.g., troubleshooting guides).
    *   Automatic or manual linking of documentation to relevant `AlertGroup`s based on the alert name (`alertname`).
*   **Jira Integration:**
    *   Ability to define rules for automatically creating Jira tickets based on alert labels.
    *   Adds comments to Jira tickets upon alert status changes (e.g., resolution).
*   **Dashboards:**
    *   **Main Dashboard:** Shows overall alert statistics (active, unacknowledged, silenced), severity/instance distribution charts, and daily alert trends.
    *   **Tier 1 Dashboard:** Lists active, unacknowledged alerts with auto-refresh and direct acknowledgement capabilities.
    *   **Admin Dashboard:** Displays overall user/comment/acknowledgement stats and links to administrative sections.
*   **User Management & Profiles:**
    *   Standard Django authentication and user management.
    *   User profiles with personal settings (e.g., Jalali/Gregorian date format preference).
    *   Access control based on user staff status.

## 3. Technical Architecture

*   **Backend Framework:** Python / Django
*   **API:** Django REST framework (DRF)
*   **Background Processing:** Celery
*   **Message Queue & Celery Result Backend:** Redis
*   **Database:** SQLite (development), PostgreSQL (recommended for production)
*   **Frontend:** Bootstrap 5, JavaScript (Vanilla JS, likely jQuery for libraries like Toastr), Chart.js, Lucide Icons (for modern UI icons)
*   **Text Editor:** TinyMCE (for documentation)
*   **Deployment:** Docker, Docker Compose

## 4. Project Structure (Django Apps)

*   **`core`:** Contains shared models, views, base templates (`base.html`, `navbar.html`, ...), template tags, context processors, and common middleware.
*   **`alerts`:** Core alert management logic. Includes models (`AlertGroup`, `AlertInstance`, `SilenceRule`, `AlertComment`, `AlertAcknowledgementHistory`), processing services, forms, views, and APIs for alerts and silence rules.
*   **`docs`:** Manages alert-related documentation. Includes models (`AlertDocumentation`, `DocumentationAlertGroup`), documentation matching service, forms, and views.
*   **`integrations`:** Handles integration with external services (currently Jira). Includes models (`JiraIntegrationRule`, `JiraRuleMatcher`), Jira service interaction logic, and views.
*   **`users`:** Manages users, profiles, and user preferences.
*   **`dashboard`:** Contains views for the various dashboards (Main, Tier 1, Admin).
*   **`sentryHub`:** Main Django project settings (`settings.py`, `urls.py`).
*   **Signals:** Django signals (specifically `alert_processed`) are used extensively to decouple alert processing logic from other modules (silence, docs, integrations). Handlers in each app listen for this signal.
*   **Services:** Core business logic (like alert processing, rule matching) is encapsulated in `services` directories within relevant apps.

## 5. Core Workflow

1.  **Receive:** Alertmanager sends a POST request to the `/alerts/api/webhook/` endpoint.
2.  **Queue:** `AlertWebhookView` validates the request and queues a Celery task (`process_alert_payload_task`) with the serialized payload in Redis.
3.  **Process Task:** A Celery worker picks up and executes the task:
    *   Parses the payload.
    *   Creates or updates the `AlertGroup` and `AlertInstance` in the database.
4.  **Dispatch Signal:** After successfully processing an `AlertGroup`/`AlertInstance` pair, the `alert_processed` signal is dispatched.
5.  **Execute Handlers:**
    *   The `alerts` app handler checks Silence Rules and mutes the `AlertGroup` if applicable.
    *   The `integrations` app handler checks Jira Rules and triggers Jira processing (likely another Celery task) if a rule matches.
    *   The `docs` app handler finds and links relevant documentation to the `AlertGroup`.
    *   (Other handlers, if implemented).
6.  **Display in UI:** The updated information in the database is displayed in the user interface via Django views and templates.

*(Refer to `documentations/workflow.md` for more details)*

## 6. Target Audience

*   **Operations Specialists:** Need to quickly review system status and identify urgent issues.
*   **System Administrators:** Need detailed reports, deeper analysis, and configuration capabilities.

## 7. Guidelines for LLM Interaction

*   This document provides a high-level overview of the SentryHub project.
*   **Avoid re-analyzing the entire `codeBase.json` to derive this basic information.**
*   Use this document to quickly understand the project's structure, goals, and workflow.
*   Frame your questions based on the information here, referencing specific sections or features.
*   If you need details about the implementation of a specific feature, mention the relevant filenames or modules for focused analysis.