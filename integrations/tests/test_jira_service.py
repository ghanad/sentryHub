# integrations/tests/test_jira_service.py

import unittest
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.conf import settings
from jira import JIRA, JIRAError
from requests.exceptions import ConnectionError
import json

# Ensure settings are configured for testing if not already
# This might be handled by Django's test runner, but good practice to be aware.
# For these unit tests, we will mock settings.JIRA_CONFIG directly.

class JiraServiceTests(TestCase):

    @patch('integrations.services.jira_service.settings')
    @patch('integrations.services.jira_service.JIRA')
    def test_init_success(self, mock_jira_class, mock_settings):
        """Test JiraService initialization with valid settings."""
        mock_settings.JIRA_CONFIG = {
            'server_url': 'http://mock-jira.com',
            'username': 'testuser',
            'password': 'testpassword',
        }
        mock_jira_instance = MagicMock()
        mock_jira_class.return_value = mock_jira_instance

        from integrations.services.jira_service import JiraService
        service = JiraService()

        mock_jira_class.assert_called_once_with(
            options={'server': 'http://mock-jira.com'},
            basic_auth=('testuser', 'testpassword'),
            timeout=10,
            max_retries=1
        )
        mock_jira_instance.myself.assert_called_once()
        self.assertIsNotNone(service.client)

    @patch('integrations.services.jira_service.settings')
    @patch('integrations.services.jira_service.JIRA')
    def test_init_missing_config(self, mock_jira_class, mock_settings):
        """Test JiraService initialization with missing settings."""
        mock_settings.JIRA_CONFIG = {
            'server_url': '', # Missing server_url
            'username': 'testuser',
            'password': 'testpassword',
        }

        from integrations.services.jira_service import JiraService
        service = JiraService()

        mock_jira_class.assert_not_called()
        self.assertIsNone(service.client)

    @patch('integrations.services.jira_service.settings')
    @patch('integrations.services.jira_service.JIRA')
    def test_init_connection_error(self, mock_jira_class, mock_settings):
        """Test JiraService initialization when connection test fails."""
        mock_settings.JIRA_CONFIG = {
            'server_url': 'http://mock-jira.com',
            'username': 'testuser',
            'password': 'testpassword',
        }
        mock_jira_instance = MagicMock()
        mock_jira_class.return_value = mock_jira_instance
        mock_jira_instance.myself.side_effect = ConnectionError("Mock connection failed")

        from integrations.services.jira_service import JiraService
        service = JiraService()

        mock_jira_class.assert_called_once()
        mock_jira_instance.myself.assert_called_once()
        self.assertIsNone(service.client) # Client should be None if connection test fails

    @patch('integrations.services.jira_service.settings')
    def test_check_connection_client_none(self, mock_settings):
        """Test check_connection when client is None due to missing config."""
        mock_settings.JIRA_CONFIG = {
            'server_url': '', # Missing server_url to cause client to be None
            'username': 'testuser',
            'password': 'testpassword',
        }
        # Need to import after patching settings
        from integrations.services.jira_service import JiraService
        service = JiraService() # __init__ will run and set client to None

        self.assertFalse(service.check_connection())

    @patch('integrations.services.jira_service.JiraService.__init__', return_value=None)
    @patch('integrations.services.jira_service.JIRA')
    def test_check_connection_success(self, mock_jira_class, mock_init):
        """Test check_connection when client is initialized and myself() succeeds."""
        from integrations.services.jira_service import JiraService
        service = JiraService()
        service.client = MagicMock() # Manually set client as __init__ is mocked

        self.assertTrue(service.check_connection())
        service.client.myself.assert_called_once()

    @patch('integrations.services.jira_service.JiraService.__init__', return_value=None)
    @patch('integrations.services.jira_service.JIRA')
    def test_check_connection_failure(self, mock_jira_class, mock_init):
        """Test check_connection when client is initialized but myself() fails."""
        from integrations.services.jira_service import JiraService
        service = JiraService()
        service.client = MagicMock() # Manually set client as __init__ is mocked
        service.client.myself.side_effect = JIRAError(status_code=401, text="Unauthorized")

        self.assertFalse(service.check_connection())
        service.client.myself.assert_called_once()

    @patch('integrations.services.jira_service.JiraService.__init__', return_value=None)
    @patch('integrations.services.jira_service.JIRA')
    def test_create_issue_success(self, mock_jira_class, mock_init):
        """Test create_issue with valid data and assignee."""
        from integrations.services.jira_service import JiraService
        service = JiraService()
        service.client = MagicMock() # Manually set client as __init__ is mocked
        mock_issue = MagicMock()
        mock_issue.key = "TEST-123"
        service.client.create_issue.return_value = mock_issue

        project_key = "TEST"
        issue_type = "Bug"
        summary = "Test Summary"
        description = "Test Description"
        assignee_name = "testuser"
        extra_fields = {"customfield_10000": "value"}

        issue_key = service.create_issue(
            project_key, issue_type, summary, description, assignee_name, **extra_fields
        )

        expected_fields = {
            'project': {'key': project_key},
            'issuetype': {'name': issue_type},
            'summary': summary,
            'description': description,
            'assignee': {'name': assignee_name},
            **extra_fields
        }
        service.client.create_issue.assert_called_once_with(fields=expected_fields)
        self.assertEqual(issue_key, "TEST-123")

    @patch('integrations.services.jira_service.JiraService.__init__', return_value=None)
    def test_add_comment_client_none(self, mock_init):
        """Test add_comment when client is None."""
        from integrations.services.jira_service import JiraService
        service = JiraService()
        service.client = None # Ensure client is None

        issue_key = "TEST-123"
        comment_body = "This is a test comment."

        self.assertFalse(service.add_comment(issue_key, comment_body))

    @patch('integrations.services.jira_service.JiraService.__init__', return_value=None)
    @patch('integrations.services.jira_service.JIRA')
    def test_add_comment_success(self, mock_jira_class, mock_init):
        """Test add_comment with valid data."""
        from integrations.services.jira_service import JiraService
        service = JiraService()
        service.client = MagicMock() # Manually set client as __init__ is mocked
        mock_comment = MagicMock()
        mock_comment.id = "10000"
        service.client.add_comment.return_value = mock_comment

        issue_key = "TEST-123"
        comment_body = "This is a test comment."

        self.assertTrue(service.add_comment(issue_key, comment_body))
        service.client.add_comment.assert_called_once_with(issue_key, body=comment_body)

    @patch('integrations.services.jira_service.JiraService.__init__', return_value=None)
    @patch('integrations.services.jira_service.JIRA')
    def test_add_comment_jira_error(self, mock_jira_class, mock_init):
        """Test add_comment when Jira API returns an error."""
        from integrations.services.jira_service import JiraService
        service = JiraService()
        service.client = MagicMock() # Manually set client as __init__ is mocked
        service.client.add_comment.side_effect = JIRAError(status_code=404, text="Issue Not Found")

        issue_key = "NONEXISTENT-123"
        comment_body = "This comment will fail."

        self.assertFalse(service.add_comment(issue_key, comment_body))
        service.client.add_comment.assert_called_once_with(issue_key, body=comment_body)

    @patch('integrations.services.jira_service.JiraService.__init__', return_value=None)
    @patch('integrations.services.jira_service.JIRA')
    def test_add_comment_connection_error(self, mock_jira_class, mock_init):
        """Test add_comment when a connection error occurs."""
        from integrations.services.jira_service import JiraService
        service = JiraService()
        service.client = MagicMock() # Manually set client as __init__ is mocked
        service.client.add_comment.side_effect = ConnectionError("Mock connection error")

        issue_key = "TEST-123"
        comment_body = "This comment will cause a connection error."

        self.assertFalse(service.add_comment(issue_key, comment_body))
        service.client.add_comment.assert_called_once_with(issue_key, body=comment_body)

    @patch('integrations.services.jira_service.JiraService.__init__', return_value=None)
    @patch('integrations.services.jira_service.JIRA')
    def test_add_comment_empty_body(self, mock_jira_class, mock_init):
        """Test add_comment with an empty comment body."""
        from integrations.services.jira_service import JiraService
        service = JiraService()
        service.client = MagicMock() # Manually set client as __init__ is mocked

        issue_key = "TEST-123"
        comment_body = ""

        self.assertTrue(service.add_comment(issue_key, comment_body))
        service.client.add_comment.assert_not_called() # add_comment should not be called for empty body

    @patch('integrations.services.jira_service.JiraService.__init__', return_value=None)
    def test_get_issue_status_category_client_none(self, mock_init):
        """Test get_issue_status_category when client is None."""
        from integrations.services.jira_service import JiraService
        service = JiraService()
        service.client = None # Ensure client is None

        issue_key = "TEST-123"

        self.assertIsNone(service.get_issue_status_category(issue_key))

    @patch('integrations.services.jira_service.JiraService.__init__', return_value=None)
    @patch('integrations.services.jira_service.JIRA')
    def test_get_issue_status_category_success(self, mock_jira_class, mock_init):
        """Test get_issue_status_category with a valid issue."""
        from integrations.services.jira_service import JiraService
        service = JiraService()
        service.client = MagicMock() # Manually set client as __init__ is mocked

        mock_status_category = MagicMock()
        mock_status_category.name = "To Do"
        mock_status = MagicMock()
        mock_status.statusCategory = mock_status_category
        mock_issue = MagicMock()
        mock_issue.fields.status = mock_status
        service.client.issue.return_value = mock_issue

        issue_key = "TEST-123"

        status_category = service.get_issue_status_category(issue_key)

        service.client.issue.assert_called_once_with(issue_key, fields='status')
        self.assertEqual(status_category, "To Do")

    @patch('integrations.services.jira_service.JiraService.__init__', return_value=None)
    @patch('integrations.services.jira_service.JIRA')
    def test_get_issue_status_category_jira_error(self, mock_jira_class, mock_init):
        """Test get_issue_status_category when Jira API returns an error."""
        from integrations.services.jira_service import JiraService
        service = JiraService()
        service.client = MagicMock() # Manually set client as __init__ is mocked
        service.client.issue.side_effect = JIRAError(status_code=404, text="Issue Not Found")

        issue_key = "NONEXISTENT-123"

        status_category = service.get_issue_status_category(issue_key)

        service.client.issue.assert_called_once_with(issue_key, fields='status')
        self.assertIsNone(status_category)

    @patch('integrations.services.jira_service.JiraService.__init__', return_value=None)
    @patch('integrations.services.jira_service.JIRA')
    def test_get_issue_status_category_connection_error(self, mock_jira_class, mock_init):
        """Test get_issue_status_category when a connection error occurs."""
        from integrations.services.jira_service import JiraService
        service = JiraService()
        service.client = MagicMock() # Manually set client as __init__ is mocked
        service.client.issue.side_effect = ConnectionError("Mock connection error")

        issue_key = "TEST-123"

        status_category = service.get_issue_status_category(issue_key)

        service.client.issue.assert_called_once_with(issue_key, fields='status')
        self.assertIsNone(status_category)

    @patch('integrations.services.jira_service.JiraService.__init__', return_value=None)
    @patch('integrations.services.jira_service.JIRA')
    def test_get_issue_status_category_missing_status_field(self, mock_jira_class, mock_init):
        """Test get_issue_status_category when the status field is missing."""
        from integrations.services.jira_service import JiraService
        service = JiraService()
        service.client = MagicMock() # Manually set client as __init__ is mocked

        mock_issue = MagicMock()
        mock_issue.fields.status = None # Simulate missing status field
        service.client.issue.return_value = mock_issue

        issue_key = "TEST-123"

        status_category = service.get_issue_status_category(issue_key)

        service.client.issue.assert_called_once_with(issue_key, fields='status')
        self.assertIsNone(status_category)

    @patch('integrations.services.jira_service.JiraService.__init__', return_value=None)
    @patch('integrations.services.jira_service.JIRA')
    def test_get_issue_status_category_missing_status_category(self, mock_jira_class, mock_init):
        """Test get_issue_status_category when the statusCategory is missing."""
        from integrations.services.jira_service import JiraService
        service = JiraService()
        service.client = MagicMock() # Manually set client as __init__ is mocked

        mock_status = MagicMock()
        mock_status.statusCategory = None # Simulate missing statusCategory
        mock_issue = MagicMock()
        mock_issue.fields.status = mock_status
        service.client.issue.return_value = mock_issue

        issue_key = "TEST-123"

        status_category = service.get_issue_status_category(issue_key)

        service.client.issue.assert_called_once_with(issue_key, fields='status')
        self.assertIsNone(status_category)
