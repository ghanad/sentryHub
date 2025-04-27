import logging
from jira import JIRA, JIRAError
from django.conf import settings

logger = logging.getLogger(__name__)

class JiraService:
    def __init__(self):
        self.client = None
        self.connected = False
        try:
            self.client = JIRA(
                server=settings.JIRA_CONFIG['server_url'],
                basic_auth=(
                    settings.JIRA_CONFIG['username'],
                    settings.JIRA_CONFIG['password']
                )
            )
            self.connected = True
        except Exception as e:
            logger.error(f"Failed to connect to Jira: {e}")

    def check_connection(self):
        return self.connected

    def create_issue(self, project_key, issue_type, summary, description):
        """
        Creates a Jira issue using a simplified field structure, similar to the test script.
        Bypasses validation and createmeta for debugging purposes.
        """
        if not self.connected:
            logger.error("Jira client is not connected. Cannot create issue.")
            return None

        # Simplified fields dictionary, mirroring the test script
        fields = {
            'project': {'key': project_key},
            'summary': summary,
            'description': description,
            'issuetype': {'name': issue_type},
        }

        logger.info(f"Attempting to create Jira issue with simplified fields: {fields}")

        try:
            issue = self.client.create_issue(fields=fields)
            logger.info(f"Successfully created issue {issue.key} in project {project_key} using simplified method.")
            return issue.key
        except JIRAError as e:
            # Log the detailed error from Jira
            logger.error(f"Jira API error during simplified issue creation. Status: {e.status_code}, Response: {e.text}", exc_info=True)
            # Add more context based on common error codes if helpful
            if e.status_code == 400:
                logger.error("Status 400 (Bad Request) often indicates missing required fields or invalid field values.")
            elif e.status_code == 401 or e.status_code == 403:
                logger.error(f"Status {e.status_code} (Unauthorized/Forbidden) indicates potential permission issues for user '{settings.JIRA_CONFIG.get('username', 'N/A')}' in project '{project_key}'.")
            elif e.status_code == 404:
                 logger.error("Status 404 (Not Found) is unusual for creation. Check project key, issue type validity, and API endpoint.")
            return None
        except Exception as e:
            # Catch any other unexpected exceptions during the process
            logger.error(f"Unexpected error during simplified Jira issue creation: {str(e)}", exc_info=True)
            return None