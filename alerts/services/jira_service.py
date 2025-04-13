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

    def create_issue(self, project_key: str, issue_type: str, summary: str, description: str, **extra_fields) -> Optional[str]:
        """ Creates a new issue in Jira. """
        if not self.is_configured or not self.client:
            logger.error("Cannot create Jira issue: Service not configured or client unavailable.")
            return None

        field_dict = {
            'project': {'key': project_key},
            'issuetype': {'name': issue_type},
            'summary': summary,
            'description': {
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
            **extra_fields
        }

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

        comment_adf = {
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
            comment = self.client.add_comment(issue_key, body=comment_adf)
            logger.info(f"Successfully added comment to Jira issue: {issue_key} (Comment ID: {comment.id})")
            return True
        except (JIRAError, ConnectionError) as e:
            status = getattr(e, 'status_code', 'N/A')
            text = getattr(e, 'text', str(e))
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

# Singleton instance (optional, depends on usage pattern)
# You might instantiate it where needed instead.
# jira_service_instance = JiraService()