# integrations/services/jira_service.py

import logging
import re
from typing import Optional, Dict, Any
from jira import JIRA, JIRAError
from django.conf import settings
from requests.exceptions import ConnectionError
import json

logger = logging.getLogger(__name__)

class JiraService:
    """
    Handles interactions with the Jira API.
    Uses 'username' and 'password' from JIRA_CONFIG.
    """
    def __init__(self):
        self.client: Optional[JIRA] = None
        try:
            config = settings.JIRA_CONFIG
            server_url = config.get('server_url')
            username = config.get('username') # Use username
            password = config.get('password') # Use password

            if server_url and username and password:
                try:
                    # Simplified options, relying on library defaults
                    options = {'server': server_url}
                    self.client = JIRA(
                        options=options,
                        basic_auth=(username, password), # Use username/password
                        timeout=10,
                        max_retries=1
                    )
                    # Light connection test after initialization
                    self.client.myself()
                    logger.info(f"Jira client initialized and connection verified for server: {server_url}")
                except (JIRAError, ConnectionError, Exception) as jira_init_error:
                    logger.error(f"Jira client initialization or connection test failed: {jira_init_error}", exc_info=True)
                    self.client = None
            else:
                logger.warning("Jira integration is not fully configured in settings (missing server_url, username, or password).")
                self.client = None
        except Exception as settings_error:
            logger.error(f"Error accessing Jira settings during JiraService initialization: {settings_error}", exc_info=True)
            self.client = None

    def check_connection(self) -> bool:
        """Checks if the Jira client was initialized and attempts a basic API call."""
        if self.client is None:
             logger.error("Jira connection check failed: Client not initialized.")
             return False
        try:
            self.client.myself()
            logger.info("Jira connection check successful (via myself()).")
            return True
        except Exception as e:
            logger.error(f"Jira live connection check failed: {e}", exc_info=True)
            if isinstance(e, JIRAError):
                 logger.error(f"JiraError details: Status={getattr(e, 'status_code', 'N/A')}, Text={getattr(e, 'text', 'N/A')}")
            return False

    def create_issue(self, project_key: str, issue_type: str, summary: str, description: str, assignee_name: Optional[str] = None, **extra_fields) -> Optional[str]:
        """ Creates a new issue in Jira, sending description as plain text and optionally setting the assignee by username. """
        if self.client is None:
            logger.error("Cannot create Jira issue: Client not initialized.")
            return None

        # Ensure the description from the task/view is treated as plain text/wiki markup
        plain_description = description.replace('\\n', '\n')

        field_dict: Dict[str, Any] = {
            'project': {'key': project_key},
            'issuetype': {'name': issue_type},
            'summary': summary,
            'description': plain_description,
            **extra_fields
        }

        if assignee_name:
            field_dict['assignee'] = {'name': assignee_name}
            logger.info(f"Attempting to assign Jira issue to username: {assignee_name}")
        else:
             logger.info("No assignee name provided, creating issue unassigned.")

        try:
            # First attempt: Create with assignee if provided
            issue = self.client.create_issue(fields=field_dict)
            logger.info(f"Successfully created Jira issue: {issue.key} in project {project_key}")
            return issue.key
        except JIRAError as e:
            status_code = getattr(e, 'status_code', 'N/A')
            simple_text = getattr(e, 'text', str(e))
            response = getattr(e, 'response', None)
            response_text = getattr(response, 'text', None)

            is_assignee_error = False
            if status_code == 400 and assignee_name and response_text and response_text.strip().startswith('{'):
                try:
                    error_json = json.loads(response_text)
                    assignee_error_msg = error_json.get('errors', {}).get('assignee')
                    # Check if the specific assignee error message exists (adapt if Jira message format differs)
                    if assignee_error_msg and (f"User '{assignee_name}' does not exist" in assignee_error_msg or f"user with username '{assignee_name}' not found" in assignee_error_msg):
                         is_assignee_error = True
                         logger.info(f"Identified assignee error from response: {assignee_error_msg}") # More specific log
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse JIRAError response text as JSON: {response_text}")
                except Exception as parse_err:
                    logger.warning(f"Error checking JIRAError JSON structure for assignee error: {parse_err}")

            if is_assignee_error:
                logger.warning(f"Assignee '{assignee_name}' not found for project {project_key}. Retrying without assignee.")
                field_dict.pop('assignee', None)
                try:
                    issue = self.client.create_issue(fields=field_dict)
                    logger.info(f"Successfully created Jira issue without assignee: {issue.key} in project {project_key}")
                    return issue.key
                except (JIRAError, ConnectionError) as retry_error:
                    retry_status = getattr(retry_error, 'status_code', 'N/A')
                    retry_text = getattr(retry_error, 'text', str(retry_error))
                    logger.error(f"Failed to create Jira issue in project {project_key} even after removing assignee: Status {retry_status} - {retry_text}", exc_info=True)
                    logger.error(f"Data sent on retry: {field_dict}")
                    return None
            else:
                logger.error(f"Failed to create Jira issue in project {project_key}: Status {status_code} - {simple_text}", exc_info=True)
                if status_code == 400:
                    logger.error(f"Data sent to Jira create issue: {field_dict}")
                return None
        except ConnectionError as e:
            logger.error(f"Connection error creating Jira issue in project {project_key}: {e}", exc_info=True)
            return None
        except Exception as e:
             logger.error(f"An unexpected error occurred creating Jira issue in project {project_key}", exc_info=True)
             return None

    def add_comment(self, issue_key: str, comment_body: str) -> bool:
        """ Adds a comment to an existing Jira issue as plain text. """
        if self.client is None:
            logger.error(f"Cannot add comment to Jira issue {issue_key}: Client not initialized.")
            return False

        plain_comment = comment_body.replace('\\n', '\n')
        if not plain_comment.strip():
            logger.warning(f"Skipping empty comment for Jira issue {issue_key}")
            return True

        try:
            comment = self.client.add_comment(issue_key, body=plain_comment)
            logger.info(f"Successfully added comment to Jira issue: {issue_key} (Comment ID: {comment.id})")
            return True
        except (JIRAError, ConnectionError) as e:
            status_code = getattr(e, 'status_code', 'N/A')
            text = getattr(e, 'text', str(e))
            if status_code == 404:
                 logger.error(f"Failed to add comment: Jira issue {issue_key} not found.")
            else:
                 logger.error(f"Failed to add comment to Jira issue {issue_key}: Status {status_code} - {text}", exc_info=True)
                 if status_code == 400:
                      logger.error(f"Data sent to Jira add comment: {plain_comment}")
            return False
        except Exception as e:
             logger.error(f"An unexpected error occurred adding comment to Jira issue {issue_key}", exc_info=True)
             return False

    def get_issue_status_category(self, issue_key: str) -> Optional[str]:
        """ Gets the status category name ('To Do', 'In Progress', 'Done') of a Jira issue. """
        if self.client is None:
            logger.error(f"Cannot get status for Jira issue {issue_key}: Client not initialized.")
            return None

        try:
            issue = self.client.issue(issue_key, fields='status')
            status_field = getattr(issue.fields, 'status', None)
            status_category_obj = getattr(status_field, 'statusCategory', None)
            status_category_name = getattr(status_category_obj, 'name', None)

            if status_category_name:
                logger.debug(f"Status category for Jira issue {issue_key} is '{status_category_name}'")
                return status_category_name
            else:
                 logger.warning(f"Could not determine status category for Jira issue {issue_key}. Status field: {status_field}")
                 return None
        except (JIRAError, ConnectionError) as e:
            status_code = getattr(e, 'status_code', 'N/A')
            text = getattr(e, 'text', str(e))
            if status_code == 404:
                 logger.warning(f"Could not get status: Jira issue {issue_key} not found.")
            else:
                 logger.error(f"Failed to get status for Jira issue {issue_key}: Status {status_code} - {text}", exc_info=True)
            return None
        except Exception as e:
             logger.error(f"An unexpected error occurred getting status for Jira issue {issue_key}", exc_info=True)
             return None

    # --- NEW METHOD ---
    def add_watcher(self, issue_key: str, username: str) -> bool:
        """ Adds a user as a watcher to an existing Jira issue by username. """
        if self.client is None:
            logger.error(f"Cannot add watcher to Jira issue {issue_key}: Client not initialized.")
            return False

        if not username:
            logger.warning(f"Skipping add watcher for Jira issue {issue_key}: No username provided.")
            return False # Cannot add watcher without username

        try:
            # The jira-python library handles adding watcher by username directly
            self.client.add_watcher(issue_key, username)
            logger.info(f"Successfully requested to add watcher '{username}' to Jira issue: {issue_key}")
            # Note: Jira API might return 204 No Content on success,
            # jira-python library call doesn't return a value here, so we assume success if no exception.
            return True
        except JIRAError as e:
            status_code = getattr(e, 'status_code', 'N/A')
            text = getattr(e, 'text', str(e))
            # Common errors:
            # 404: Issue not found
            # 400/401/403: User not found, permission issue, watching disabled, etc.
            if status_code == 404:
                 logger.error(f"Failed to add watcher '{username}': Jira issue {issue_key} not found.")
            elif status_code == 400:
                 logger.error(f"Failed to add watcher '{username}' to issue {issue_key}: Bad request (Status {status_code}). Check if user exists and has permission. Response: {text}", exc_info=False) # Don't need full traceback usually
            elif status_code == 401 or status_code == 403:
                 logger.error(f"Failed to add watcher '{username}' to issue {issue_key}: Permission denied (Status {status_code}). Check user permissions and if watching is enabled. Response: {text}", exc_info=False)
            else:
                 logger.error(f"Failed to add watcher '{username}' to Jira issue {issue_key}: Status {status_code} - {text}", exc_info=True)
            return False
        except ConnectionError as e:
            logger.error(f"Connection error adding watcher '{username}' to Jira issue {issue_key}: {e}", exc_info=True)
            return False
        except Exception as e:
             logger.error(f"An unexpected error occurred adding watcher '{username}' to Jira issue {issue_key}", exc_info=True)
             return False