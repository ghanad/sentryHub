# integrations/services/jira_service.py

import logging
import re
from typing import Optional, Dict, Any
from jira import JIRA, JIRAError
from django.conf import settings
from requests.exceptions import ConnectionError

logger = logging.getLogger(__name__)

class JiraService:
    """
    Handles interactions with the Jira API.
    Uses 'username' and 'password' from JIRA_CONFIG.
    Reverted to simpler options based on previous working state.
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
                    # --- Revert options to simple state ---
                    # Rely on library's auto-detection for version
                    # Remove validate=False and explicit version
                    options = {'server': server_url}
                    # ---------------------------------------
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

    # --- متدهای create_issue, add_comment, get_issue_status_category ---
    # از نسخه قبلی (که description را به صورت رشته ساده ارسال می‌کرد) کپی کنید
    # ... (Copy create_issue, add_comment, get_issue_status_category from the previous response) ...
    def create_issue(self, project_key: str, issue_type: str, summary: str, description: str, assignee_name: Optional[str] = None, **extra_fields) -> Optional[str]:
        """ Creates a new issue in Jira, sending description as plain text and optionally setting the assignee by username. """
        if self.client is None: # Check client directly
            logger.error("Cannot create Jira issue: Client not initialized.")
            return None

        # Ensure the description from the task/view is treated as plain text/wiki markup
        # Replace explicit '\\n' with actual newlines for Jira Wiki Markup if needed,
        # but plain text with newlines usually works.
        plain_description = description.replace('\\n', '\n')

        field_dict: Dict[str, Any] = {
            'project': {'key': project_key},
            'issuetype': {'name': issue_type},
            'summary': summary,
            'description': plain_description, # Send the string directly
            **extra_fields
        }

        # Add assignee using username if provided, matching the working test script
        if assignee_name:
            field_dict['assignee'] = {'name': assignee_name}
            logger.info(f"Attempting to assign Jira issue to username: {assignee_name}")
        else:
             logger.info("No assignee name provided, creating issue unassigned.")


        try:
            # Log the final dictionary being sent ONLY if debugging is needed
            # logger.debug(f"Sending data to Jira create issue: {field_dict}")
            issue = self.client.create_issue(fields=field_dict)
            logger.info(f"Successfully created Jira issue: {issue.key} in project {project_key}")
            return issue.key
        except (JIRAError, ConnectionError) as e:
            status_code = getattr(e, 'status_code', 'N/A')
            text = getattr(e, 'text', str(e))
            logger.error(f"Failed to create Jira issue in project {project_key}: Status {status_code} - {text}", exc_info=True)
            # Log the data sent if it's a 400 error
            if status_code == 400:
                 logger.error(f"Data sent to Jira create issue: {field_dict}")
            return None
        except Exception as e:
             logger.error(f"An unexpected error occurred creating Jira issue in project {project_key}", exc_info=True)
             return None

    def add_comment(self, issue_key: str, comment_body: str) -> bool:
        """ Adds a comment to an existing Jira issue as plain text. """
        if self.client is None:
            logger.error(f"Cannot add comment to Jira issue {issue_key}: Client not initialized.")
            return False

        # Send comment body directly as string
        plain_comment = comment_body.replace('\\n', '\n')
        if not plain_comment.strip():
            logger.warning(f"Skipping empty comment for Jira issue {issue_key}")
            return True # Or False depending on desired behavior for empty comments

        try:
            comment = self.client.add_comment(issue_key, body=plain_comment) # Send string directly
            logger.info(f"Successfully added comment to Jira issue: {issue_key} (Comment ID: {comment.id})")
            return True
        except (JIRAError, ConnectionError) as e:
            status_code = getattr(e, 'status_code', 'N/A')
            text = getattr(e, 'text', str(e))
            if status_code == 404:
                 logger.error(f"Failed to add comment: Jira issue {issue_key} not found.")
            else:
                 logger.error(f"Failed to add comment to Jira issue {issue_key}: Status {status_code} - {text}", exc_info=True)
                 # Log data sent on 400 error
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
            # Request only the status field for efficiency
            issue = self.client.issue(issue_key, fields='status')
            # Access status category name safely
            status_field = getattr(issue.fields, 'status', None)
            status_category_obj = getattr(status_field, 'statusCategory', None)
            status_category_name = getattr(status_category_obj, 'name', None)

            if status_category_name:
                logger.debug(f"Status category for Jira issue {issue_key} is '{status_category_name}'")
                return status_category_name
            else:
                 logger.warning(f"Could not determine status category for Jira issue {issue_key}. Status field: {status_field}")
                 return None # Return None if category cannot be determined
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

    # Removed get_user_account_id method as it was failing and is not needed
    # if assigning by username works directly.