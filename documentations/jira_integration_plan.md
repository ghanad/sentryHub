# SentryHub - Jira Integration Implementation Plan

**Overall Goal:** Add functionality to the SentryHub (Django) project to automatically create and update Jira issues based on alerts received from Alertmanager, considering matching rules, alert statuses, and issue statuses.

**Target Audience:** This document is prepared for an AI coding assistant (like Claude or Cursor) to guide the step-by-step implementation of this feature.

**Project Structure:**
* **Main Project:** SentryHub
* **Relevant Apps:** `alerts`, `core`, `main_dashboard`
* **Core Alert Processing:** `alerts.services.alerts_processor.AlertProcessor`
* **Core Models:** `alerts.models.Alert`, `alerts.models.AlertGroup`, `alerts.models.AlertInstance`
* **Key Technologies:** Django, Celery (for background tasks), `jira-python` (for Jira API interaction)

---

## Prerequisites and Initial Setup

1.  **Install Jira Library:**
    * Add the `jira` library to your `requirements.txt` file:
        ```
        jira>=3.0 # Or the latest stable version
        ```
    * Then run: `pip install -r requirements.txt`

2.  **Celery Setup:**
    * Ensure Celery and Celery Beat are correctly configured and running in the project (based on existing `settings.py`, `celery.py`, and potentially `docker-compose.yml` files). All Jira interactions **must** be performed via Celery tasks.

3.  **Jira Connection Configuration:**
    * Jira connection details (Jira server URL, username/email, and API Token) must be managed securely.
    * **Recommended Method:** Use Environment Variables.
    * Add `python-dotenv` to `requirements.txt` (if not already present) and create a `.env` file in the project root:
        ```dotenv
        # .env
        JIRA_SERVER_URL=[https://your-domain.atlassian.net](https://your-domain.atlassian.net)
        JIRA_API_USER=your-email@example.com
        JIRA_API_TOKEN=your_generated_api_token
        ```
    * Read these values in your `settings.py` file:
        ```python
        # settings.py
        import os
        from dotenv import load_dotenv

        load_dotenv() # Loads variables from .env file

        JIRA_CONFIG = {
            'server_url': os.getenv('JIRA_SERVER_URL'),
            'api_user': os.getenv('JIRA_API_USER'),
            'api_token': os.getenv('JIRA_API_TOKEN'),
            # Other default or configurable values (can be added later)
            'default_project_key': 'OPS', # Example
            'default_issue_type': 'Task', # Example
            'open_status_categories': ['To Do', 'In Progress'], # Jira status categories considered 'Open'
            'closed_status_categories': ['Done'], # Jira status categories considered 'Closed'
        }

        # Ensure essential values exist
        if not all([JIRA_CONFIG['server_url'], JIRA_CONFIG['api_user'], JIRA_CONFIG['api_token']]):
            # You can log a Warning or raise an Error in production environments
            print("WARNING: Jira configuration is incomplete. Jira integration might not work.")
            # import logging
            # logger = logging.getLogger(__name__)
            # logger.warning("Jira configuration is incomplete. Jira integration might not work.")

        # Add SITE_URL for generating links back to SentryHub
        SITE_URL = os.getenv('SITE_URL', 'http://localhost:8000') # Default for local dev
        ```
    * **Security Note:** Never hardcode tokens or passwords directly in the code or `settings.py`.

---

## Task Breakdown

This feature will be implemented in several steps (Tasks). Please complete only one Task at a time.

### Task 1: Create Base Jira Service

* **Objective:** Create a service class to manage the connection and basic interactions with the Jira API.
* **Files:** `alerts/services/jira_service.py` (Create or modify)
* **Steps:**
    1.  Create the file `alerts/services/jira_service.py` if it doesn't exist.
    2.  Import necessary libraries (`from jira import JIRA, JIRAError`, `from django.conf import settings`, `import logging`, `from requests.exceptions import ConnectionError`).
    3.  Define a logger for this service (`logger = logging.getLogger(__name__)`).
    4.  Create the `JiraService` class.
    5.  In the class `__init__`, use `settings.JIRA_CONFIG` to create and store a JIRA client instance. Handle errors if configuration is missing or the initial connection fails.
    ```python
    # alerts/services/jira_service.py
    import logging
    from typing import Optional
    from jira import JIRA, JIRAError
    from django.conf import settings
    from requests.exceptions import ConnectionError

    logger = logging.getLogger(__name__)

    class JiraService:
        """
        Handles interactions with the Jira API.
        """
        def __init__(self):
            self.client: Optional[JIRA] = None
            self.is_configured: bool = False
            config = settings.JIRA_CONFIG
            server_url = config.get('server_url')
            api_user = config.get('api_user')
            api_token = config.get('api_token')

            if server_url and api_user and api_token:
                try:
                    # Reduce default timeout (optional, default is high)
                    options = {'server': server_url, 'rest_api_version': '3'} # Specify API v3
                    self.client = JIRA(
                        options=options,
                        basic_auth=(api_user, api_token),
                        timeout=10, # Set timeout in seconds
                        max_retries=1 # Limit retries
                    )
                    # Test connection by getting server info (can be resource intensive)
                    # self.client.server_info()
                    self.is_configured = True
                    logger.info(f"Jira client initialized for server: {server_url}")
                except JIRAError as e:
                    logger.error(f"Jira connection failed during initialization: Status {e.status_code} - {e.text}", exc_info=True)
                except ConnectionError as e:
                    logger.error(f"Jira connection failed: Could not connect to server {server_url}", exc_info=True)
                except Exception as e:
                    logger.error(f"An unexpected error occurred during Jira client initialization", exc_info=True)
            else:
                logger.warning("Jira integration is not configured in settings.")

        def check_connection(self) -> bool:
            """Checks if the Jira client is configured and potentially tests the connection."""
            if not self.is_configured or not self.client:
                logger.error("Jira client is not configured or failed to initialize.")
                return False
            try:
                # A lightweight check, like getting server info (can sometimes fail on permissions)
                # Or try fetching projects the user can see
                self.client.projects(maxResults=1)
                logger.info("Jira connection check successful.")
                return True
            except (JIRAError, ConnectionError, Exception) as e:
                logger.error(f"Jira connection check failed: {e}", exc_info=True)
                return False

    # Singleton instance (optional, depends on usage pattern)
    # You might instantiate it where needed instead.
    # jira_service_instance = JiraService()
    ```
* **Testing:** Write a simple test (in `alerts/tests/test_services.py`) that instantiates `JiraService` and (using Mock for `jira.JIRA`) verifies that it attempts connection if settings are present and logs appropriately if not.

### Task 2: Database Model Changes (`AlertGroup`)

* **Objective:** Add a field to store the Jira issue key associated with each alert group.
* **Files:** `alerts/models.py`, `alerts/migrations/`
* **Steps:**
    1.  Edit the `AlertGroup` model in `alerts/models.py`.
    2.  Add a new `CharField` named `jira_issue_key`. Allow it to be null/blank and add a database index for faster lookups.
    ```python
    # alerts/models.py
    from django.db import models

    class AlertGroup(models.Model):
        # ... existing fields ...
        fingerprint = models.CharField(max_length=64, unique=True, db_index=True)
        status = models.CharField(max_length=20, choices=[('firing', 'Firing'), ('resolved', 'Resolved'), ('pending', 'Pending')], default='pending', db_index=True)
        labels = models.JSONField(default=dict, help_text="Common labels for the alert group")
        annotations = models.JSONField(default=dict, help_text="Common annotations for the alert group")
        first_seen = models.DateTimeField(auto_now_add=True, db_index=True)
        last_seen = models.DateTimeField(auto_now=True, db_index=True)
        is_silenced = models.BooleanField(default=False, db_index=True)
        silenced_until = models.DateTimeField(null=True, blank=True)
        silence_rule = models.ForeignKey('SilenceRule', on_delete=models.SET_NULL, null=True, blank=True, related_name='silenced_groups')
        # ... other fields like comments, acknowledgements relationships ...

        # --- New Field ---
        jira_issue_key = models.CharField(
            max_length=50,
            null=True,
            blank=True,
            db_index=True,
            verbose_name="Jira Issue Key",
            help_text="The key of the Jira issue associated with this alert group (e.g., PROJECT-123)."
        )
        # --- End New Field ---

        # ... existing methods like get_common_label ...

        def __str__(self):
             # Include jira_issue_key if it exists
             common_alert_name = self.get_common_label('alertname', self.fingerprint)
             base_str = f"AlertGroup {common_alert_name} ({self.status})"
             if self.jira_issue_key:
                 base_str += f" [Jira: {self.jira_issue_key}]"
             return base_str

        def get_common_label(self, label_name: str, default: str = None) -> Optional[str]:
            """Helper to safely get a common label."""
            return self.labels.get(label_name, default)

    ```
    3.  Run the following commands to create and apply the migration:
        ```bash
        python manage.py makemigrations alerts
        python manage.py migrate
        ```
* **Testing:** Check the migration file. Write a test for the `AlertGroup` model (or update an existing one) to ensure the `jira_issue_key` field exists and can be set and saved.

### Task 3: Define Jira Integration Rule Models

* **Objective:** Create data models to store rules that determine which alerts should trigger Jira issue creation/updates.
* **Files:** `alerts/models.py`, `alerts/migrations/`
* **Steps:**
    1.  In `alerts/models.py`, create two new models: `JiraIntegrationRule` and `JiraRuleMatcher`. Their structure can be similar to `SilenceRule` and `SilenceRuleMatcher`.
    ```python
    # alerts/models.py
    from django.db import models
    from django.core.exceptions import ValidationError
    import json # For JSON validation

    class JiraRuleMatcher(models.Model):
        """
        A single matcher criterion for a JiraIntegrationRule, based on alert labels.
        Uses JSONField for flexibility. Example: {"severity": "critical", "namespace": "prod-.*"}
        Values can be exact strings or regex patterns.
        """
        name = models.CharField(max_length=100, help_text="Identifier for this matcher set")
        # Store match criteria as JSON: {"label_name": "value_or_regex", ...}
        match_criteria = models.JSONField(
            default=dict,
            help_text='JSON object where keys are label names and values are exact strings or regex patterns to match. Example: {"severity": "critical", "cluster": "prod-us-east-.*"}'
        )
        is_regex = models.BooleanField(default=False, help_text="Set to True if any values in match_criteria are regex patterns.")
        created_at = models.DateTimeField(auto_now_add=True)
        updated_at = models.DateTimeField(auto_now=True)

        def clean(self):
            """ Validate that match_criteria is a valid JSON dictionary. """
            super().clean()
            if not isinstance(self.match_criteria, dict):
                raise ValidationError({'match_criteria': 'Must be a valid JSON object (dictionary).'})
            # Optional: Further validation for keys/values if needed

        def __str__(self):
            # Provide a more informative representation
            try:
                criteria_str = json.dumps(self.match_criteria, ensure_ascii=False, indent=None)
                return f"{self.name}: {criteria_str} (Regex: {self.is_regex})"
            except TypeError:
                 return f"{self.name}: Invalid JSON (Regex: {self.is_regex})"


    class JiraIntegrationRule(models.Model):
        """
        Defines a rule for creating/updating Jira issues based on alert properties.
        """
        name = models.CharField(max_length=100, unique=True)
        description = models.TextField(blank=True)
        is_active = models.BooleanField(default=True, db_index=True)
        # Matchers define WHICH alerts trigger this rule. A rule matches if ALL its matchers are satisfied.
        matchers = models.ManyToManyField(
            'JiraRuleMatcher',
            related_name='rules',
             help_text="Select one or more matchers. The rule applies if ALL selected matchers match the alert's labels."
        )
        # Action defines WHAT happens in Jira
        jira_project_key = models.CharField(max_length=50, help_text="Target Jira project key (e.g., OPS)")
        jira_issue_type = models.CharField(max_length=50, help_text="Target Jira issue type (e.g., Bug, Task)")
        # Optional: Define priority if multiple rules might match
        priority = models.IntegerField(default=0, help_text="Higher priority rules are evaluated first.")
        created_at = models.DateTimeField(auto_now_add=True)
        updated_at = models.DateTimeField(auto_now=True)

        class Meta:
            ordering = ['-priority', 'name'] # Process higher priority first
            verbose_name = "Jira Integration Rule"
            verbose_name_plural = "Jira Integration Rules"

        def __str__(self):
            status = "Active" if self.is_active else "Inactive"
            return f"{self.name} ({status}, Prio: {self.priority})"

    ```
    2.  Run the migration commands:
        ```bash
        python manage.py makemigrations alerts
        python manage.py migrate
        ```
* **Testing:** Check the migration files. Write model tests for `JiraIntegrationRule` and `JiraRuleMatcher`, including validation for the `match_criteria` field.

### Task 4: Implement Jira Rule Matching Logic

* **Objective:** Create a service to find the `JiraIntegrationRule` that matches an alert's labels.
* **Files:** `alerts/services/jira_matcher.py` (Create), `alerts/tests/test_services.py`
* **Steps:**
    1.  Create the file `alerts/services/jira_matcher.py`.
    2.  Implement the `JiraRuleMatcherService` class. It should have a method that takes alert labels and returns the first active, matching rule based on `priority`.
    3.  The matching logic must check the `JiraRuleMatcher`s associated with each rule. A rule matches only if **ALL** its associated matchers are satisfied by the alert labels. Use regex matching if `is_regex=True`, otherwise use exact string matching.
    ```python
    # alerts/services/jira_matcher.py
    import logging
    import re
    from typing import Dict, Optional, List

    from alerts.models import JiraIntegrationRule, JiraRuleMatcher

    logger = logging.getLogger(__name__)

    class JiraRuleMatcherService:
        """
        Finds the first matching JiraIntegrationRule for a given set of alert labels.
        """

        def find_matching_rule(self, alert_labels: Dict[str, str]) -> Optional[JiraIntegrationRule]:
            """
            Finds the highest priority, active JiraIntegrationRule where ALL associated
            matchers match the given alert labels.

            Args:
                alert_labels: A dictionary representing the labels of an alert.

            Returns:
                The matching JiraIntegrationRule instance, or None if no rule matches.
            """
            # Get active rules, ordered by priority (highest first)
            # Prefetch related matchers for efficiency
            active_rules = JiraIntegrationRule.objects.filter(is_active=True).prefetch_related('matchers').order_by('-priority', 'name')

            for rule in active_rules:
                if self._does_rule_match(rule, alert_labels):
                    logger.debug(f"Alert labels matched Jira rule: {rule.name} (ID: {rule.id})")
                    return rule

            logger.debug("No active Jira integration rule matched the alert labels.")
            return None

        def _does_rule_match(self, rule: JiraIntegrationRule, alert_labels: Dict[str, str]) -> bool:
            """ Checks if ALL matchers associated with the rule match the alert labels. """
            # If a rule has no matchers, should it match? Assume no.
            if not rule.matchers.exists():
                 logger.debug(f"Jira rule '{rule.name}' (ID: {rule.id}) has no matchers defined, skipping.")
                 return False

            # Check if all associated matchers are satisfied
            all_matchers_satisfied = True
            for matcher in rule.matchers.all():
                if not self._does_matcher_match(matcher, alert_labels):
                    all_matchers_satisfied = False
                    # logger.debug(f"Matcher '{matcher.name}' (ID: {matcher.id}) did not match for rule '{rule.name}'.")
                    break # No need to check other matchers for this rule

            return all_matchers_satisfied


        def _does_matcher_match(self, matcher: JiraRuleMatcher, alert_labels: Dict[str, str]) -> bool:
            """ Checks if a single matcher's criteria are met by the alert labels. """
            # If a matcher has no criteria, should it match? Assume yes (vacuously true).
            if not matcher.match_criteria:
                return True

            for label_key, match_value in matcher.match_criteria.items():
                if label_key not in alert_labels:
                    # Required label is missing in the alert
                    # logger.debug(f"Matcher '{matcher.name}': Required label '{label_key}' not found in alert labels.")
                    return False

                alert_value = alert_labels[label_key]
                expected_value = str(match_value) # Ensure comparison is string-based
                actual_value = str(alert_value)

                if matcher.is_regex:
                    try:
                        if not re.fullmatch(expected_value, actual_value):
                            # Regex does not match
                            # logger.debug(f"Matcher '{matcher.name}': Regex '{expected_value}' did not match value '{actual_value}' for label '{label_key}'.")
                            return False
                    except re.error:
                        logger.error(f"Invalid regex pattern '{expected_value}' in JiraRuleMatcher ID {matcher.id}", exc_info=True)
                        # Treat invalid regex as non-matching
                        return False
                else:
                    if actual_value != expected_value:
                        # Exact string does not match
                        # logger.debug(f"Matcher '{matcher.name}': Value '{actual_value}' did not match expected value '{expected_value}' for label '{label_key}'.")
                        return False

            # If we reached here, all criteria in this specific matcher were satisfied
            logger.debug(f"Matcher '{matcher.name}' (ID: {matcher.id}) criteria met by alert labels.")
            return True

    # Optional: Singleton instance if preferred
    # jira_matcher_service_instance = JiraRuleMatcherService()
    ```
* **Testing:** Write comprehensive tests for `JiraRuleMatcherService`. Cover various scenarios: exact match, regex match, no match, active/inactive rules, priority ordering, presence/absence of labels, invalid regex, rules with zero or multiple matchers, and the logic requiring *all* matchers to pass.

### Task 5: Enhance Jira Service (Core API Functions)

* **Objective:** Add the core functions for interacting with Jira (create issue, add comment, get issue status) to `JiraService`.
* **Files:** `alerts/services/jira_service.py`, `alerts/tests/test_services.py`
* **Steps:**
    1.  Edit the `JiraService` class in `alerts/services/jira_service.py`.
    2.  Add the following methods:
        * `create_issue(self, project_key: str, issue_type: str, summary: str, description: str, **extra_fields) -> Optional[str]:`
            * Use `self.client.create_issue(...)`.
            * Take `summary` and `description` as input.
            * Take `project_key` and `issue_type` as input.
            * Allow passing extra fields (like `labels`, `priority`, custom fields) via `**extra_fields`.
            * Return the `issue.key` (e.g., 'PROJECT-123') on success.
            * Log errors (`JIRAError`, `ConnectionError`) and return `None` on failure.
        * `add_comment(self, issue_key: str, comment_body: str) -> bool:`
            * Use `self.client.add_comment(issue_key, comment_body)`.
            * Return `True` on success, `False` on failure (log the error).
        * `get_issue_status_category(self, issue_key: str) -> Optional[str]:`
            * Fetch the issue using `self.client.issue(issue_key, fields='status')`.
            * Return `issue.fields.status.statusCategory.name` (e.g., 'To Do', 'In Progress', 'Done').
            * Log errors or issue-not-found cases and return `None` on failure.
    3.  Before each API call, check if `self.client` is initialized and `self.is_configured` is `True`.
    ```python
    # alerts/services/jira_service.py
    # ... (import statements and __init__ from Task 1) ...

    class JiraService:
        # ... (__init__ and check_connection methods) ...

        def create_issue(self, project_key: str, issue_type: str, summary: str, description: str, **extra_fields) -> Optional[str]:
            """ Creates a new issue in Jira. """
            if not self.is_configured or not self.client:
                logger.error("Cannot create Jira issue: Service not configured or client unavailable.")
                return None

            field_dict = {
                'project': {'key': project_key},
                'issuetype': {'name': issue_type},
                'summary': summary,
                'description': { # Use Atlassian Document Format (ADF) for richer descriptions
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": description
                                }
                            ]
                        }
                    ]
                },
                **extra_fields # Allows adding labels, components, custom fields etc.
            }
            # Example: adding labels
            # if 'labels' in extra_fields:
            #     field_dict['labels'] = extra_fields['labels']

            try:
                issue = self.client.create_issue(fields=field_dict)
                logger.info(f"Successfully created Jira issue: {issue.key} in project {project_key}")
                return issue.key
            except (JIRAError, ConnectionError) as e:
                status = getattr(e, 'status_code', 'N/A')
                text = getattr(e, 'text', str(e))
                logger.error(f"Failed to create Jira issue in project {project_key}: Status {status} - {text}", exc_info=True)
                return None
            except Exception as e:
                 logger.error(f"An unexpected error occurred creating Jira issue in project {project_key}", exc_info=True)
                 return None


        def add_comment(self, issue_key: str, comment_body: str) -> bool:
            """ Adds a comment to an existing Jira issue using ADF. """
            if not self.is_configured or not self.client:
                logger.error(f"Cannot add comment to Jira issue {issue_key}: Service not configured or client unavailable.")
                return False

            comment_adf = { # Use Atlassian Document Format (ADF)
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": comment_body
                            }
                        ]
                    }
                ]
            }

            try:
                # Use the body parameter for ADF
                comment = self.client.add_comment(issue_key, body=comment_adf)
                logger.info(f"Successfully added comment to Jira issue: {issue_key} (Comment ID: {comment.id})")
                return True
            except (JIRAError, ConnectionError) as e:
                status = getattr(e, 'status_code', 'N/A')
                text = getattr(e, 'text', str(e))
                # Check for specific error like issue not found (status 404)
                if status == 404:
                     logger.error(f"Failed to add comment: Jira issue {issue_key} not found.")
                else:
                     logger.error(f"Failed to add comment to Jira issue {issue_key}: Status {status} - {text}", exc_info=True)
                return False
            except Exception as e:
                 logger.error(f"An unexpected error occurred adding comment to Jira issue {issue_key}", exc_info=True)
                 return False

        def get_issue_status_category(self, issue_key: str) -> Optional[str]:
            """ Gets the status category name ('To Do', 'In Progress', 'Done') of a Jira issue. """
            if not self.is_configured or not self.client:
                logger.error(f"Cannot get status for Jira issue {issue_key}: Service not configured or client unavailable.")
                return None

            try:
                # Request only the status field for efficiency
                issue = self.client.issue(issue_key, fields='status')
                status_category = issue.fields.status.statusCategory.name
                logger.debug(f"Status category for Jira issue {issue_key} is '{status_category}'")
                return status_category
            except (JIRAError, ConnectionError) as e:
                status = getattr(e, 'status_code', 'N/A')
                text = getattr(e, 'text', str(e))
                if status == 404:
                     logger.warning(f"Could not get status: Jira issue {issue_key} not found.")
                else:
                     logger.error(f"Failed to get status for Jira issue {issue_key}: Status {status} - {text}", exc_info=True)
                return None
            except Exception as e:
                 logger.error(f"An unexpected error occurred getting status for Jira issue {issue_key}", exc_info=True)
                 return None
    ```
* **Testing:** Write unit tests for each of these methods in `alerts/tests/test_services.py`. Use `unittest.mock` to mock the `jira` client and simulate successful and unsuccessful API responses (including 404s, 403s, 500s).

### Task 6: Create Celery Tasks

* **Objective:** Define Celery tasks to perform Jira operations asynchronously in the background.
* **Files:** `alerts/tasks.py` (Create or modify), `sentryhub/celery.py` (Ensure task discovery)
* **Steps:**
    1.  Create the file `alerts/tasks.py` if it doesn't exist.
    2.  Import necessary libraries and models (`from celery import shared_task, Task`, `from .services.jira_service import JiraService`, `from .models import AlertGroup, JiraIntegrationRule, AlertInstance`, `import logging`, `from django.conf import settings`, `from django.utils import timezone`, `from django.urls import reverse`, `import json`).
    3.  Define a logger.
    4.  Define the main task `process_jira_for_alert_group` using the `@shared_task` decorator. It should accept the alert group ID, matching rule ID, and the current alert status ('firing'/'resolved') as input.
    5.  (Optional but recommended) Consider defining smaller tasks for specific Jira actions (create, add_comment) called by the main task. This simplifies testing and management. Implement retry logic, especially for API calls.
    ```python
    # alerts/tasks.py
    import logging
    import json
    from typing import Optional, Dict, Any

    from celery import shared_task, Task
    from django.conf import settings
    from django.utils import timezone
    from django.urls import reverse
    from django.core.exceptions import ObjectDoesNotExist

    from .services.jira_service import JiraService
    from .models import AlertGroup, JiraIntegrationRule, AlertInstance

    logger = logging.getLogger(__name__)

    # Base task with retry logic for API calls might be useful
    class JiraTaskBase(Task):
        # Example: Retry on common transient errors (adjust exceptions as needed)
        # autoretry_for = (ConnectionError, TimeoutError) # Add relevant JiraError status codes if possible
        retry_kwargs = {'max_retries': 3, 'countdown': 15} # Example: Retry 3 times, wait 15s
        retry_backoff = True
        retry_jitter = True # Add randomness to wait time


    @shared_task(bind=True, base=JiraTaskBase) # Use bind=True for self (task instance) access
    def process_jira_for_alert_group(self, alert_group_id: int, rule_id: int, alert_status: str):
        """
        Main Celery task to handle Jira integration logic for an alert group.
        Triggered when an alert matches a JiraIntegrationRule.

        Args:
            self: The task instance (due to bind=True).
            alert_group_id: The ID of the AlertGroup.
            rule_id: The ID of the matching JiraIntegrationRule.
            alert_status: The current status of the alert ('firing' or 'resolved').
        """
        logger.info(f"Starting Jira processing task {self.request.id} for AlertGroup ID: {alert_group_id}, Rule ID: {rule_id}, Status: {alert_status}")

        try:
            alert_group = AlertGroup.objects.select_related('silence_rule').get(pk=alert_group_id)
            rule = JiraIntegrationRule.objects.get(pk=rule_id)
            # Get the latest instance for context
            latest_instance = alert_group.instances.order_by('-received_at').first()
        except AlertGroup.DoesNotExist:
            logger.error(f"Task {self.request.id}: AlertGroup with ID {alert_group_id} not found. Aborting Jira task.")
            return # No retry needed if object doesn't exist
        except JiraIntegrationRule.DoesNotExist:
            logger.error(f"Task {self.request.id}: JiraIntegrationRule with ID {rule_id} not found. Aborting Jira task.")
            return # No retry needed
        except Exception as e:
             logger.error(f"Task {self.request.id}: Error fetching objects for AlertGroup {alert_group_id}: {e}", exc_info=True)
             # May want to retry depending on the error
             raise # Reraise to potentially trigger retry

        jira_service = JiraService()
        if not jira_service.is_configured:
            logger.error(f"Task {self.request.id}: Jira service not configured. Aborting Jira task.")
            # No retry if config is missing.
            return

        existing_issue_key = alert_group.jira_issue_key
        issue_status_category = None

        if existing_issue_key:
            logger.debug(f"Task {self.request.id}: AlertGroup {alert_group_id} has existing Jira key: {existing_issue_key}. Checking status.")
            try:
                 issue_status_category = jira_service.get_issue_status_category(existing_issue_key)
            except Exception as e:
                 logger.error(f"Task {self.request.id}: Failed to get status for Jira issue {existing_issue_key}: {e}", exc_info=True)
                 # Trigger retry? Could be a transient API issue.
                 self.retry(exc=e) # Use Celery's retry mechanism

            if issue_status_category is None and jira_service.is_configured: # Handle case where status check failed definitively (e.g., 404)
                logger.warning(f"Task {self.request.id}: Could not get status for Jira issue {existing_issue_key} (possibly deleted or inaccessible). Clearing local key.")
                alert_group.jira_issue_key = None
                try:
                    alert_group.save(update_fields=['jira_issue_key'])
                except Exception as db_err:
                    logger.error(f"Task {self.request.id}: Failed to clear jira_issue_key for AlertGroup {alert_group_id} after status check failure: {db_err}", exc_info=True)
                    self.retry(exc=db_err) # Retry on DB error
                existing_issue_key = None # Proceed as if no key existed


        # --- Logic based on alert status and Jira issue status ---

        open_categories = settings.JIRA_CONFIG.get('open_status_categories', ['To Do', 'In Progress'])
        closed_categories = settings.JIRA_CONFIG.get('closed_status_categories', ['Done'])

        try: # Wrap main logic in try/except for retry handling
            if alert_status == 'firing':
                if existing_issue_key:
                    if issue_status_category in open_categories:
                        # Issue exists and is open: Add a comment
                        comment = f"Alert group '{alert_group.fingerprint}' is firing again at {timezone.now().isoformat()}."
                        if latest_instance:
                             comment += f"\nLatest details summary: {latest_instance.summary or 'N/A'}"
                        logger.info(f"Task {self.request.id}: Adding 'firing again' comment to open Jira issue: {existing_issue_key}")
                        success = jira_service.add_comment(existing_issue_key, comment)
                        if not success: raise Exception(f"Failed to add comment to {existing_issue_key}")
                        # Potentially update other fields (e.g., last_seen custom field) here
                    elif issue_status_category in closed_categories:
                        # Issue exists but is closed: Create a NEW issue
                        logger.info(f"Task {self.request.id}: Existing Jira issue {existing_issue_key} is closed. Creating a new issue for firing alert group {alert_group_id}.")
                        alert_group.jira_issue_key = None # Clear old key before creating new
                        alert_group.save(update_fields=['jira_issue_key'])
                        # Fall through to the 'create new issue' block below
                    else:
                         # Status is neither clearly open nor closed (or unknown category)
                         logger.warning(f"Task {self.request.id}: Jira issue {existing_issue_key} has status category '{issue_status_category}' which is not configured as open or closed. Adding comment anyway.")
                         comment = f"Alert firing again (status category '{issue_status_category}') for group '{alert_group.fingerprint}' at {timezone.now().isoformat()}."
                         success = jira_service.add_comment(existing_issue_key, comment)
                         if not success: raise Exception(f"Failed to add comment to {existing_issue_key} (unknown status)")

                if not alert_group.jira_issue_key: # Handles 'no key initially' and 'key cleared'
                    # Create a new issue
                    alert_name = alert_group.get_common_label('alertname', 'N/A')
                    severity = alert_group.get_common_label('severity', 'default').capitalize()
                    summary = f"[{severity}] SentryHub Alert: {latest_instance.summary if latest_instance else alert_name}"[:250] # Limit summary length

                    # Construct description with more details using Jira Markdown (subset of ADF)
                    try:
                         sentryhub_url_path = reverse('alerts:alert_detail', args=[alert_group.fingerprint])
                         full_sentryhub_url = f"{settings.SITE_URL}{sentryhub_url_path}"
                    except Exception:
                         full_sentryhub_url = "N/A (Check SITE_URL setting and URL config)"

                    description_parts = [
                        f"*Alert Group Fingerprint:* {alert_group.fingerprint}",
                        f"*Status:* Firing",
                        f"*First Seen:* {alert_group.first_seen.isoformat()}",
                        f"*Last Seen:* {alert_group.last_seen.isoformat()}",
                        "\n*Labels:*",
                        "{code:json}",
                        json.dumps(alert_group.labels, indent=2),
                        "{code}",
                        "\n*Annotations:*",
                        "{code:json}",
                        json.dumps(alert_group.annotations, indent=2),
                        "{code}",
                        f"\n*Latest Alert Summary:* {latest_instance.summary if latest_instance else 'N/A'}",
                        f"*Latest Alert Description:* {latest_instance.description if latest_instance else 'N/A'}",
                        f"\n[Link to SentryHub|{full_sentryhub_url}]"
                    ]
                    description = "\n".join(description_parts)

                    logger.info(f"Task {self.request.id}: Creating new Jira issue for alert group {alert_group_id} in project {rule.jira_project_key}")
                    # Add extra fields like labels based on alert labels if desired
                    jira_labels = ['sentryhub', alert_group.get_common_label('severity', 'default')]
                    # Add more labels from the alert if needed, ensure they are valid Jira labels (no spaces etc.)
                    for key, value in alert_group.labels.items():
                         # Basic sanitization for Jira labels
                         sanitized_label = re.sub(r'[^\w-]+', '_', f"{key}_{value}")[:255]
                         if len(sanitized_label) > 0:
                              jira_labels.append(sanitized_label)

                    extra_fields = {'labels': list(set(jira_labels))} # Use set to remove duplicates

                    new_issue_key = jira_service.create_issue(
                        project_key=rule.jira_project_key,
                        issue_type=rule.jira_issue_type,
                        summary=summary,
                        description=description.strip(),
                        **extra_fields
                    )
                    if new_issue_key:
                        alert_group.jira_issue_key = new_issue_key
                        alert_group.save(update_fields=['jira_issue_key'])
                        logger.info(f"Task {self.request.id}: Associated AlertGroup {alert_group_id} with new Jira issue {new_issue_key}")
                    else:
                        # Creation failed, task might retry based on base class
                        logger.error(f"Task {self.request.id}: Failed to create Jira issue for AlertGroup {alert_group_id}.")
                        raise Exception(f"Jira issue creation failed for AlertGroup {alert_group_id}")


            elif alert_status == 'resolved':
                if existing_issue_key and issue_status_category in open_categories:
                    # Issue exists and is open: Add a 'resolved' comment
                    resolved_time = timezone.now().isoformat()
                    comment = f"Alert group '{alert_group.fingerprint}' was resolved at {resolved_time}."
                    logger.info(f"Task {self.request.id}: Adding 'resolved' comment to open Jira issue: {existing_issue_key}")
                    success = jira_service.add_comment(existing_issue_key, comment)
                    if not success: raise Exception(f"Failed to add resolved comment to {existing_issue_key}")
                    # Consider if you want to automatically transition the Jira issue status here (more complex)
                    # Or maybe automatically clear the local key? Depends on desired workflow.
                    # For now, just add comment. Manual closure in Jira is often preferred.
                elif existing_issue_key:
                    logger.info(f"Task {self.request.id}: Alert group {alert_group_id} resolved, but Jira issue {existing_issue_key} has status '{issue_status_category}'. No comment added.")
                else:
                    logger.info(f"Task {self.request.id}: Alert group {alert_group_id} resolved, but no associated Jira issue found. No action taken.")

        except Exception as e:
            # Catch exceptions during the main logic (API calls, DB saves)
            logger.error(f"Task {self.request.id}: An error occurred during Jira processing for AlertGroup {alert_group_id}: {e}", exc_info=True)
            # Retry the task using Celery's mechanism
            self.retry(exc=e)

        logger.info(f"Finished Jira processing task {self.request.id} for AlertGroup ID: {alert_group_id}")

    ```
    * **Important:** Ensure these tasks are discovered by Celery, usually by importing them or the module in your `sentryhub/celery.py` (or wherever the Celery app is defined).

* **Testing:** Write unit tests for the Celery task(s). Test the logic inside the task (fetching objects, calling `JiraService`, updating `AlertGroup`) by mocking the Jira service and models. Test that the expected behavior (logging, no retry, or retry) occurs under different error conditions (object not found, API error).

### Task 7: Integrate into Alert Processor (`AlertProcessor`)

* **Objective:** Trigger the Celery task from within `AlertProcessor` when an alert matches a Jira rule.
* **Files:** `alerts/services/alerts_processor.py`
* **Steps:**
    1.  Import the `JiraRuleMatcherService` and the `process_jira_for_alert_group` task.
    2.  In the `process_alert` method (or similar method handling the `AlertGroup`) within `AlertProcessor`:
        * **After** processing and saving the `AlertGroup` and `AlertInstance`.
        * **After** checking for Silence Rules (if the alert is silenced, do nothing for Jira).
        * Instantiate `JiraRuleMatcherService` (or use a singleton).
        * Call the `find_matching_rule` method using `alert_group.labels`.
        * **If** a `matching_rule` is found:
            * Call `process_jira_for_alert_group.delay(alert_group.id, matching_rule.id, alert_group.status)`. Pass the current `alert_group.status` ('firing' or 'resolved').
    ```python
    # alerts/services/alerts_processor.py
    import logging
    # ... other imports ...
    from .models import AlertGroup, AlertInstance, SilenceRule # Ensure SilenceRule is imported if used
    from .services.silence_matcher import SilenceMatcherService # Assuming this exists and is used
    from .services.jira_matcher import JiraRuleMatcherService # Import the new service
    from .tasks import process_jira_for_alert_group # Import the Celery task

    logger = logging.getLogger(__name__)
    # Instantiate services (or use singletons if designed that way)
    silence_service = SilenceMatcherService()
    jira_matcher_service = JiraRuleMatcherService()


    class AlertProcessor:
        # ... existing methods like __init__, _calculate_fingerprint, _get_or_create_alert_group, _create_alert_instance ...

        def process_alert(self, alert_data: dict):
            """ Processes a single alert from the Alertmanager payload. """
            logger.debug(f"Processing alert: {alert_data.get('labels', {}).get('alertname', 'N/A')}")
            # ... (logic to parse alert_data, get labels, annotations, status, startsAt, endsAt etc.) ...
            fingerprint = self._calculate_fingerprint(alert_data['labels']) # Assuming this method exists
            alert_group, group_created = self._get_or_create_alert_group(fingerprint, alert_data)
            alert_instance = self._create_alert_instance(alert_group, alert_data)

            # Update AlertGroup status based on the incoming alert
            # This logic should exist already, ensure it correctly sets alert_group.status
            current_alert_status = alert_data.get('status', 'firing') # 'firing' or 'resolved'
            if alert_group.status != current_alert_status:
                 alert_group.status = current_alert_status
                 # Update last_seen as well potentially
                 alert_group.last_seen = alert_instance.received_at
                 alert_group.save(update_fields=['status', 'last_seen']) # Ensure status is saved before checking below
            # else: # Even if status hasn't changed, update last_seen for firing alerts
            #     if current_alert_status == 'firing':
            #         alert_group.last_seen = alert_instance.received_at
            #         alert_group.save(update_fields=['last_seen'])


            # --- Silence Check ---
            is_silenced, _ = silence_service.check_alert(alert_group.labels) # Simplified check return value
            alert_group.is_silenced = is_silenced # Update the group's silenced status
            # Persist silence status change if needed (e.g., for display)
            # alert_group.save(update_fields=['is_silenced']) # If check_alert doesn't save it

            if is_silenced:
                logger.info(f"Alert group {fingerprint} is currently silenced. Skipping Jira integration.")
                # Proceed with other processing if needed, but exit Jira logic
                # ... (rest of the processing like notifications if applicable even when silenced) ...
                return alert_group, alert_instance # Or however the flow continues

            # --- Jira Integration Check (Only if NOT silenced) ---
            logger.debug(f"Checking Jira rules for non-silenced alert group {fingerprint} with status {alert_group.status}")
            matching_rule = jira_matcher_service.find_matching_rule(alert_group.labels)

            if matching_rule:
                logger.info(f"Alert group {fingerprint} matched Jira rule '{matching_rule.name}'. Triggering Jira processing task.")
                try:
                    process_jira_for_alert_group.delay(
                        alert_group_id=alert_group.id,
                        rule_id=matching_rule.id,
                        alert_status=alert_group.status # Pass the CURRENT status of the group
                    )
                except Exception as e:
                     # Handle potential errors during task queuing (e.g., Celery broker down)
                     logger.error(f"Failed to queue Jira processing task for alert group {alert_group.id}: {e}", exc_info=True)
                     # Decide how to handle this - maybe log and continue?
            else:
                logger.debug(f"No Jira rule matched for alert group {fingerprint}.")


            # ... (rest of the processing, e.g., notifications, history saving) ...
            return alert_group, alert_instance

        # ... other helper methods like _calculate_fingerprint, _get_or_create_alert_group, _create_alert_instance ...
    ```
* **Testing:** Update or write integration tests for `AlertProcessor`. Simulate receiving an alert, verify that `find_matching_rule` is called, and if a match occurs, verify that `process_jira_for_alert_group.delay` is called with the correct arguments (mock the Celery task). Also, test that the Jira task is **not** called if the alert is silenced or if no rule matches.

### Task 8: Admin Interface for Jira Rules

* **Objective:** Enable management (CRUD) of `JiraIntegrationRule` and `JiraRuleMatcher` via the Django Admin interface.
* **Files:** `alerts/admin.py`
* **Steps:**
    1.  Import the `JiraIntegrationRule` and `JiraRuleMatcher` models.
    2.  Create a `admin.ModelAdmin` for `JiraRuleMatcher` (can be simple or display `match_criteria` more effectively).
    3.  Create a `admin.ModelAdmin` for `JiraIntegrationRule`. Use `filter_horizontal` or `filter_vertical` for the `matchers` ManyToManyField to allow selecting existing matchers easily. Include important fields like `name`, `is_active`, `priority`, `jira_project_key`, `jira_issue_type` in `list_display` and `list_filter`.
    4.  Register the models with the Admin site.
    5.  Optionally, add `jira_issue_key` to the `AlertGroup` admin display.
    ```python
    # alerts/admin.py
    from django.contrib import admin
    from django.utils.safestring import mark_safe
    import json

    from .models import (
        # ... other models like AlertGroup, AlertInstance ...
        JiraIntegrationRule,
        JiraRuleMatcher,
        AlertGroup # Import AlertGroup if modifying its admin
    )

    @admin.register(JiraRuleMatcher)
    class JiraRuleMatcherAdmin(admin.ModelAdmin):
        list_display = ('name', 'get_criteria_preview', 'is_regex', 'created_at')
        search_fields = ('name', 'match_criteria')
        list_filter = ('is_regex',)
        readonly_fields = ('created_at', 'updated_at')

        def get_criteria_preview(self, obj):
            """ Provides a formatted, truncated preview of the criteria JSON. """
            try:
                # Use mark_safe with <pre> for better formatting
                pretty_json = json.dumps(obj.match_criteria, indent=2, ensure_ascii=False)
                preview = f'<pre style="white-space: pre-wrap; word-wrap: break-word; max-width: 400px; display: inline-block;">{pretty_json}</pre>'
                return mark_safe(preview)
            except Exception:
                return "Invalid JSON"
        get_criteria_preview.short_description = "Match Criteria"


    @admin.register(JiraIntegrationRule)
    class JiraIntegrationRuleAdmin(admin.ModelAdmin):
        list_display = ('name', 'is_active', 'priority', 'jira_project_key', 'jira_issue_type', 'matcher_count', 'updated_at')
        list_filter = ('is_active', 'jira_project_key', 'jira_issue_type')
        search_fields = ('name', 'description', 'jira_project_key', 'matchers__name') # Search by matcher name too
        ordering = ('-priority', 'name')
        filter_horizontal = ('matchers',) # Use filter_horizontal for ManyToMany selection

        readonly_fields = ('created_at', 'updated_at')
        fieldsets = (
            (None, {
                'fields': ('name', 'description', 'is_active', 'priority')
            }),
            ('Jira Action Configuration', {
                'fields': ('jira_project_key', 'jira_issue_type')
            }),
            ('Matchers (Rule matches if ALL selected matchers apply)', { # Clarify matching logic
                'fields': ('matchers',) # Uses filter_horizontal defined above
            }),
             ('Timestamps', {
                'fields': ('created_at', 'updated_at'),
                'classes': ('collapse',) # Optional: hide by default
            }),
        )

        def matcher_count(self, obj):
            return obj.matchers.count()
        matcher_count.short_description = "# Matchers"

        # Optional: Add validation in admin save
        # def save_model(self, request, obj, form, change):
        #     if not obj.matchers.exists():
        #         # Add a warning message - Django admin messages framework
        #         messages.warning(request, f"Rule '{obj.name}' has no matchers and will likely never match any alerts.")
        #     super().save_model(request, obj, form, change)


    # --- Modify existing AlertGroupAdmin (if it exists) ---
    # Find the existing registration for AlertGroup and modify it
    # Example assuming AlertGroupAdmin is already defined somewhere in this file or imported

    # Unregister first if it's already registered
    try:
        admin.site.unregister(AlertGroup)
    except admin.sites.NotRegistered:
        pass # Wasn't registered, proceed

    @admin.register(AlertGroup)
    class AlertGroupAdmin(admin.ModelAdmin): # Define or redefine
         # Combine existing fields with the new one
         list_display = ('fingerprint', 'get_alert_name', 'status', 'first_seen', 'last_seen', 'jira_issue_key_link', 'is_silenced') # Add jira_issue_key_link
         list_filter = ('status', 'is_silenced')
         search_fields = ('fingerprint', 'labels', 'annotations', 'jira_issue_key') # Add jira_issue_key
         # Make most fields read-only in admin as they come from Alertmanager
         readonly_fields = (
             'fingerprint', 'status', 'labels', 'annotations',
             'first_seen', 'last_seen', 'created_at', 'updated_at',
             'is_silenced', 'silenced_until', 'silence_rule',
             'jira_issue_key', # Make the key itself read-only here
             'jira_issue_key_link' # Display the link as read-only too
         )
         fieldsets = (
             ('Core Information', {
                 'fields': ('fingerprint', 'status', 'first_seen', 'last_seen')
             }),
             ('Details', {
                 'fields': ('labels', 'annotations') # Consider using a JSON widget or formatting
             }),
             ('Status & Integrations', {
                 'fields': ('is_silenced', 'silenced_until', 'silence_rule', 'jira_issue_key_link'), # Use the link field
             }),
             ('Timestamps', {
                 'fields': ('created_at', 'updated_at'),
                 'classes': ('collapse',)
             }),
         )

         def get_alert_name(self, obj):
            return obj.get_common_label('alertname', obj.fingerprint[:12] + '...') # Show alertname or truncated fingerprint
         get_alert_name.short_description = 'Alert Name / Fingerprint'
         get_alert_name.admin_order_field = 'labels__alertname' # Allow sorting if possible

         def jira_issue_key_link(self, obj):
            """Displays the Jira key as a link if configured and key exists."""
            if obj.jira_issue_key:
                 jira_url = settings.JIRA_CONFIG.get('server_url')
                 if jira_url:
                      # Ensure URL doesn't have trailing slash before appending
                      base_url = jira_url.rstrip('/')
                      issue_url = f"{base_url}/browse/{obj.jira_issue_key}"
                      return mark_safe(f'<a href="{issue_url}" target="_blank">{obj.jira_issue_key}</a>')
                 else:
                      return obj.jira_issue_key # Fallback to text if server URL not set
            return "-" # Display dash if no key
         jira_issue_key_link.short_description = 'Jira Issue'
         jira_issue_key_link.admin_order_field = 'jira_issue_key'


    # Ensure other essential models like AlertInstance, SilenceRule, etc., are also registered.
    # Check existing admin registrations.

    ```
* **Testing:** Access the Django Admin interface. Verify you can Create, Read, Update, and Delete Jira rules and matchers. Check that the display fields, filters, and search work correctly. Verify the `jira_issue_key` (as a link if possible) appears in the `AlertGroup` admin view.

### Task 9: Basic User Interface (Non-Admin) for Jira Rules

* **Objective:** Create web pages for regular users to view and manage (CRUD) `JiraIntegrationRule`s.
* **Files:**
    * `alerts/views.py`
    * `alerts/forms.py`
    * `alerts/urls.py`
    * `alerts/templates/alerts/` (Create new templates)
* **Steps:**
    1.  **Forms:** In `alerts/forms.py`, create a `ModelForm` for `JiraIntegrationRule`. You might need a custom widget or handling for the `matchers` ManyToManyField (e.g., `forms.ModelMultipleChoiceField` with `CheckboxSelectMultiple` widget, or allow selecting existing `JiraRuleMatcher`s). Create a separate `ModelForm` for `JiraRuleMatcher` if you want users to manage matchers independently.
    2.  **Views:** In `alerts/views.py`, create Class-Based Views (CBVs) for List (`ListView`), Detail (`DetailView`), Create (`CreateView`), Update (`UpdateView`), and Delete (`DeleteView`) for `JiraIntegrationRule`. Use `LoginRequiredMixin` and potentially `PermissionRequiredMixin` for access control. Follow the patterns from the existing `SilenceRule` views (`SilenceRuleListView`, `SilenceRuleCreateView`, etc.).
    3.  **Templates:**
        * Create the necessary HTML templates in `alerts/templates/alerts/`:
            * `jira_rule_list.html`: Display the list of rules.
            * `jira_rule_detail.html`: Show details of a rule (including its matchers).
            * `jira_rule_form.html`: Form for creating/editing rules.
            * `jira_rule_confirm_delete.html`: Deletion confirmation page.
        * Inherit from the base template: `{% extends 'main_dashboard/base_modern.html' %}`.
        * Follow the styling and structure from existing `SilenceRule` templates (`silence_rule_list.html`, `silence_rule_form.html`) and the design guidelines (`sentryhub-modern-design-guideline.md`).
        * Include appropriate links between pages (list, create, edit, delete).
    4.  **URLs:** In `alerts/urls.py`, define URL patterns for the new views (e.g., using the path prefix `jira-rules/`).
    5.  **Navigation:** Add a link to the Jira Rules list page (`jira_rule_list`) in the main navigation menu (likely within `core/templates/core/navbar.html` or `main_dashboard/templates/main_dashboard/base_modern.html`).
* **Testing:** Manually test the new web pages (create, view, edit, delete Jira rules). Write Django tests (using the test `Client` in `alerts/tests/test_views.py`) to cover these views and forms.

### Task 10: Jira Connection Settings UI (Optional/Basic)

* **Objective:** Create a page to display the Jira connection settings (read-only for now).
* **Files:**
    * `core/views.py` (or a new `integrations` app)
    * `core/urls.py`
    * `core/templates/core/`
* **Steps:**
    1.  **View:** Create a simple view (e.g., `TemplateView` or a function-based view) in `core/views.py`. Read the Jira settings from `settings.JIRA_CONFIG` and pass relevant, non-sensitive parts to the template context. **Never display the API Token in the template!** Only show the URL, user, and whether the token *is set* or *not set*.
    2.  **Template:** Create a template (`core/templates/core/jira_settings.html`). Display the information. Explain that the primary configuration is done via environment variables.
    3.  **URL:** Define a URL for this view in `core/urls.py` (e.g., `settings/jira/`).
    4.  **Navigation:** Add a link to this page in the settings section of the main navigation.
* **Testing:** Manually check the settings page to ensure sensitive information (API token) is NOT displayed and the connection status is indicated correctly.

### Task 11: Final Integration and End-to-End Testing

* **Objective:** Ensure the entire workflow functions correctly from receiving an alert to creating/updating a Jira issue (using API mocking).
* **Files:** `alerts/tests/test_integration.py` (or similar), `send_fake_data/` scripts
* **Steps:**
    1.  Define an end-to-end test scenario:
        * Send a `firing` alert payload that matches an active Jira rule (using `send_fake_data.py` or the Django test client).
        * Verify that the Celery task `process_jira_for_alert_group` is queued with the correct arguments.
        * Execute the Celery task directly in the test (using `task.run(...)`) while mocking the `JiraService`.
        * Assert that the mocked `create_issue` method on `JiraService` was called with the expected details.
        * Assert that the `jira_issue_key` field on the corresponding `AlertGroup` is updated with the mocked return value (e.g., 'TEST-1').
    2.  Test other key scenarios:
        * Sending the same `firing` alert again: Verify `get_issue_status_category` and then `add_comment` are called on the mock.
        * Sending a `resolved` alert: Verify `get_issue_status_category` and then `add_comment` (with a resolved message) are called.
        * Sending a `firing` alert for an issue that is mocked as 'Done' in Jira: Verify `get_issue_status_category` is called, then `create_issue` is called (to create a *new* issue), and the `jira_issue_key` on the `AlertGroup` is updated.
        * Sending an alert that does not match any rule: Verify the Celery task is NOT called.
        * Sending an alert that is silenced: Verify the Celery task is NOT called.
* **Testing Guidelines:** Refer to the `TESTING_GUIDELINES_FOR_AI.md` file.

---

## Future Enhancements (Out of Initial Scope)

* **Delayed Issue Creation:** Implement functionality where Jira issues are only created if an alert remains unacknowledged for a specific duration (e.g., 1 hour). This requires tracking acknowledgment status and using Celery Beat for periodic checks.
* **Advanced Configuration:** Allow configuration of custom Jira fields, open/closed statuses, issue priority, component assignment, etc., via the UI.
* **Two-Way Sync:** Update alert status in SentryHub if the Jira issue status changes (very complex).
* **Debouncing/Throttling:** Prevent excessive comments in Jira for rapidly firing alerts.

---

**Final Notes:**

* **Logging:** Implement detailed and meaningful logging throughout the process for debugging.
* **Error Handling:** Robustly handle potential errors (network issues, Jira API errors, logical errors) in the `JiraService` and Celery tasks. Celery's retry mechanisms are essential here.
* **Performance:** Be mindful that Jira API calls can be slow. Proper use of Celery for asynchronous processing and optimizing database queries is important.
* **Security:** Secure handling of Jira connection credentials is paramount. Use environment variables or a dedicated secrets management system.