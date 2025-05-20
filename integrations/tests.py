# integrations/tests.py
from django.test import TestCase
from django.core.exceptions import ValidationError
from integrations.models import JiraIntegrationRule

class JiraIntegrationRuleModelTests(TestCase):

    def test_create_jira_integration_rule(self):
        """
        Test creating a basic JiraIntegrationRule instance.
        """
        rule = JiraIntegrationRule.objects.create(
            name="Test Rule 1",
            match_criteria={"severity": "critical"},
            jira_project_key="TEST",
            jira_issue_type="Bug",
            jira_title_template="Alert: {{ alertname }}",
            jira_description_template="Details: {{ labels }}"
        )
        self.assertEqual(rule.name, "Test Rule 1")
        self.assertEqual(rule.match_criteria, {"severity": "critical"})
        self.assertEqual(rule.jira_project_key, "TEST")
        self.assertEqual(rule.jira_issue_type, "Bug")
        self.assertTrue(rule.is_active) # Check default is_active
        self.assertEqual(rule.priority, 0) # Check default priority
        self.assertEqual(rule.watchers, "") # Check default watchers
        self.assertEqual(rule.assignee, "") # Check default assignee

    def test_match_criteria_default(self):
        """
        Test that match_criteria defaults to an empty dictionary.
        """
        rule = JiraIntegrationRule.objects.create(
            name="Test Rule With Default Match Criteria",
            jira_project_key="TEST",
            jira_issue_type="Task"
        )
        self.assertEqual(rule.match_criteria, {})

    def test_clean_method_valid_match_criteria(self):
        """
        Test that the clean method passes with valid dictionary match_criteria.
        """
        rule = JiraIntegrationRule(
            name="Test Rule Clean Valid",
            match_criteria={"job": "node_exporter"},
            jira_project_key="TEST",
            jira_issue_type="Bug"
        )
        try:
            rule.full_clean()
        except ValidationError:
            self.fail("full_clean raised ValidationError unexpectedly!")

    def test_clean_method_invalid_match_criteria(self):
        """
        Test that the clean method raises ValidationError for invalid match_criteria.
        """
        rule = JiraIntegrationRule(
            name="Test Rule Clean Invalid",
            match_criteria="not a dictionary", # Invalid data
            jira_project_key="TEST",
            jira_issue_type="Bug"
        )
        with self.assertRaises(ValidationError) as cm:
            rule.full_clean()
        self.assertIn('match_criteria', cm.exception.message_dict)
        self.assertIn('Must be a valid JSON object (dictionary).', cm.exception.message_dict['match_criteria'])

    def test_str_representation_active(self):
        """
        Test the __str__ method for an active rule.
        """
        rule = JiraIntegrationRule.objects.create(
            name="Active Rule",
            is_active=True,
            jira_project_key="TEST",
            jira_issue_type="Task"
        )
        self.assertEqual(str(rule), "Active Rule (Active, Prio: 0)")

    def test_str_representation_inactive(self):
        """
        Test the __str__ method for an inactive rule.
        """
        rule = JiraIntegrationRule.objects.create(
            name="Inactive Rule",
            is_active=False,
            jira_project_key="TEST",
            jira_issue_type="Task",
            priority=10
        )
        self.assertEqual(str(rule), "Inactive Rule (Inactive, Prio: 10)")

    def test_get_assignee_with_assignee(self):
        """
        Test get_assignee method when assignee is set.
        """
        rule = JiraIntegrationRule.objects.create(
            name="Rule with Assignee",
            jira_project_key="TEST",
            jira_issue_type="Task",
            assignee="testuser"
        )
        self.assertEqual(rule.get_assignee(), "testuser")

    def test_get_assignee_without_assignee(self):
        """
        Test get_assignee method when assignee is not set.
        """
        rule = JiraIntegrationRule.objects.create(
            name="Rule without Assignee",
            jira_project_key="TEST",
            jira_issue_type="Task",
            assignee="" # Explicitly empty
        )
        self.assertIsNone(rule.get_assignee())

        rule_no_assignee_field = JiraIntegrationRule.objects.create(
            name="Rule without Assignee Field",
            jira_project_key="TEST",
            jira_issue_type="Task"
            # Assignee field is not provided, defaults to blank
        )
        self.assertIsNone(rule_no_assignee_field.get_assignee())


from unittest.mock import patch, MagicMock
from jira.exceptions import JIRAError
from requests.exceptions import ConnectionError
from django.conf import settings

from .services.jira_service import JiraService


class JiraServiceTests(TestCase):
    def setUp(self):
        self.valid_jira_config = {
            'server': 'https://test.jira.com',
            'username': 'user',
            'api_token': 'token',
            'project_key': 'PROJECT',
            'issue_type': 'Bug',
            'use_ssl': True,
        }

    @patch('integrations.services.jira_service.settings')
    @patch('integrations.services.jira_service.JIRA')
    def test_initialization_success(self, mock_jira, mock_settings):
        mock_settings.JIRA_CONFIG = self.valid_jira_config
        mock_jira_instance = MagicMock()
        mock_jira.return_value = mock_jira_instance

        service = JiraService()
        self.assertEqual(service.client, mock_jira_instance)
        mock_jira.assert_called_once_with(
            server=self.valid_jira_config['server'],
            basic_auth=(self.valid_jira_config['username'], self.valid_jira_config['api_token']),
            options={'verify': self.valid_jira_config['use_ssl']}
        )

    @patch('integrations.services.jira_service.settings')
    def test_initialization_missing_settings(self, mock_settings):
        mock_settings.JIRA_CONFIG = {}  # Missing JIRA_CONFIG
        with self.assertRaises(ValueError) as context:
            JiraService()
        self.assertIn("JIRA_CONFIG is not defined in settings", str(context.exception))

    @patch('integrations.services.jira_service.settings')
    @patch('integrations.services.jira_service.JIRA', side_effect=JIRAError("JIRA error"))
    def test_initialization_jira_error(self, mock_jira, mock_settings):
        mock_settings.JIRA_CONFIG = self.valid_jira_config
        with self.assertRaises(JIRAError):
            JiraService()

    @patch('integrations.services.jira_service.settings')
    @patch('integrations.services.jira_service.JIRA', side_effect=ConnectionError("Connection error"))
    def test_initialization_connection_error(self, mock_jira, mock_settings):
        mock_settings.JIRA_CONFIG = self.valid_jira_config
        with self.assertRaises(ConnectionError):
            JiraService()

    @patch('integrations.services.jira_service.settings')
    @patch('integrations.services.jira_service.JIRA')
    def test_check_connection_success(self, mock_jira, mock_settings):
        mock_settings.JIRA_CONFIG = self.valid_jira_config
        mock_jira_instance = MagicMock()
        mock_jira_instance.myself.return_value = {'name': 'testuser'}
        mock_jira.return_value = mock_jira_instance

        service = JiraService()
        self.assertTrue(service.check_connection())
        mock_jira_instance.myself.assert_called_once()

    def test_check_connection_client_not_initialized(self):
        service = JiraService.__new__(JiraService)  # Create instance without calling __init__
        service.client = None
        with self.assertRaises(ValueError) as context:
            service.check_connection()
        self.assertIn("Jira client not initialized.", str(context.exception))

    @patch('integrations.services.jira_service.settings')
    @patch('integrations.services.jira_service.JIRA')
    def test_check_connection_myself_raises_jira_error(self, mock_jira, mock_settings):
        mock_settings.JIRA_CONFIG = self.valid_jira_config
        mock_jira_instance = MagicMock()
        mock_jira_instance.myself.side_effect = JIRAError("Failed to get user")
        mock_jira.return_value = mock_jira_instance

        service = JiraService()
        with self.assertRaises(JIRAError):
            service.check_connection()
        mock_jira_instance.myself.assert_called_once()

    @patch('integrations.services.jira_service.settings')
    @patch('integrations.services.jira_service.JIRA')
    def test_check_connection_myself_raises_connection_error(self, mock_jira, mock_settings):
        mock_settings.JIRA_CONFIG = self.valid_jira_config
        mock_jira_instance = MagicMock()
        mock_jira_instance.myself.side_effect = ConnectionError("Connection failed")
        mock_jira.return_value = mock_jira_instance

        service = JiraService()
        with self.assertRaises(ConnectionError):
            service.check_connection()
        mock_jira_instance.myself.assert_called_once()

    @patch('integrations.services.jira_service.settings')
    @patch('integrations.services.jira_service.JIRA')
    def test_create_issue_success(self, mock_jira, mock_settings):
        mock_settings.JIRA_CONFIG = self.valid_jira_config
        mock_jira_instance = MagicMock()
        mock_jira.return_value = mock_jira_instance
        mock_issue = MagicMock()
        mock_issue.key = 'PROJECT-123'
        mock_jira_instance.create_issue.return_value = mock_issue

        service = JiraService()
        issue = service.create_issue("Test Summary", "Test Description", "Task")
        self.assertEqual(issue.key, 'PROJECT-123')
        mock_jira_instance.create_issue.assert_called_once_with(
            project=self.valid_jira_config['project_key'],
            summary="Test Summary",
            description="Test Description",
            issuetype={'name': "Task"},
            assignee=None
        )

    @patch('integrations.services.jira_service.settings')
    @patch('integrations.services.jira_service.JIRA')
    def test_create_issue_with_assignee_success(self, mock_jira, mock_settings):
        mock_settings.JIRA_CONFIG = self.valid_jira_config
        mock_jira_instance = MagicMock()
        mock_jira.return_value = mock_jira_instance
        mock_issue = MagicMock()
        mock_issue.key = 'PROJECT-124'
        mock_jira_instance.create_issue.return_value = mock_issue

        service = JiraService()
        issue = service.create_issue("Test Summary Assignee", "Test Description Assignee", "Bug", assignee="test_assignee")
        self.assertEqual(issue.key, 'PROJECT-124')
        mock_jira_instance.create_issue.assert_called_once_with(
            project=self.valid_jira_config['project_key'],
            summary="Test Summary Assignee",
            description="Test Description Assignee",
            issuetype={'name': "Bug"},
            assignee={'name': "test_assignee"}
        )

    def test_create_issue_client_not_initialized(self):
        service = JiraService.__new__(JiraService)  # Create instance without calling __init__
        service.client = None
        with self.assertRaises(ValueError) as context:
            service.create_issue("Test", "Desc", "Bug")
        self.assertIn("Jira client not initialized.", str(context.exception))

    @patch('integrations.services.jira_service.settings')
    @patch('integrations.services.jira_service.JIRA')
    def test_create_issue_jira_error(self, mock_jira, mock_settings):
        mock_settings.JIRA_CONFIG = self.valid_jira_config
        mock_jira_instance = MagicMock()
        mock_jira_instance.create_issue.side_effect = JIRAError("Failed to create issue")
        mock_jira.return_value = mock_jira_instance

        service = JiraService()
        with self.assertRaises(JIRAError):
            service.create_issue("Test", "Desc", "Bug")
        mock_jira_instance.create_issue.assert_called_once()

    @patch('integrations.services.jira_service.settings')
    @patch('integrations.services.jira_service.JIRA')
    def test_create_issue_connection_error(self, mock_jira, mock_settings):
        mock_settings.JIRA_CONFIG = self.valid_jira_config
        mock_jira_instance = MagicMock()
        mock_jira_instance.create_issue.side_effect = ConnectionError("Connection failed")
        mock_jira.return_value = mock_jira_instance

        service = JiraService()
        with self.assertRaises(ConnectionError):
            service.create_issue("Test", "Desc", "Bug")
        mock_jira_instance.create_issue.assert_called_once()

    @patch('integrations.services.jira_service.settings')
    @patch('integrations.services.jira_service.JIRA')
    def test_create_issue_assignee_not_found_retry_success(self, mock_jira, mock_settings):
        mock_settings.JIRA_CONFIG = self.valid_jira_config
        mock_jira_instance = MagicMock()
        mock_issue_no_assignee = MagicMock()
        mock_issue_no_assignee.key = 'PROJECT-125'

        # Simulate JIRAError for assignee not found, then success on retry
        mock_jira_instance.create_issue.side_effect = [
            JIRAError(text="assignee does not exist"),
            mock_issue_no_assignee
        ]
        mock_jira.return_value = mock_jira_instance

        service = JiraService()
        issue = service.create_issue("Test Retry", "Test Retry Desc", "Story", assignee="unknown_user")

        self.assertEqual(issue.key, 'PROJECT-125')
        self.assertEqual(mock_jira_instance.create_issue.call_count, 2)

        # Check first call with assignee
        mock_jira_instance.create_issue.assert_any_call(
            project=self.valid_jira_config['project_key'],
            summary="Test Retry",
            description="Test Retry Desc",
            issuetype={'name': "Story"},
            assignee={'name': "unknown_user"}
        )
        # Check second call without assignee
        mock_jira_instance.create_issue.assert_called_with(
            project=self.valid_jira_config['project_key'],
            summary="Test Retry",
            description="Test Retry Desc",
            issuetype={'name': "Story"},
            assignee=None
        )

    @patch('integrations.services.jira_service.settings')
    @patch('integrations.services.jira_service.JIRA')
    def test_create_issue_assignee_not_found_retry_fails_non_assignee_error(self, mock_jira, mock_settings):
        mock_settings.JIRA_CONFIG = self.valid_jira_config
        mock_jira_instance = MagicMock()

        # Simulate JIRAError not related to assignee
        mock_jira_instance.create_issue.side_effect = JIRAError(text="Some other JIRA error")
        mock_jira.return_value = mock_jira_instance

        service = JiraService()
        with self.assertRaises(JIRAError) as context:
            service.create_issue("Test No Retry", "Test No Retry Desc", "Epic", assignee="any_user")

        self.assertNotIn("assignee does not exist", str(context.exception).lower())
        self.assertEqual(mock_jira_instance.create_issue.call_count, 1)
        mock_jira_instance.create_issue.assert_called_once_with(
            project=self.valid_jira_config['project_key'],
            summary="Test No Retry",
            description="Test No Retry Desc",
            issuetype={'name': "Epic"},
            assignee={'name': "any_user"}
        )

    @patch('integrations.services.jira_service.settings')
    @patch('integrations.services.jira_service.JIRA')
    def test_add_comment_success(self, mock_jira, mock_settings):
        mock_settings.JIRA_CONFIG = self.valid_jira_config
        mock_jira_instance = MagicMock()
        mock_jira.return_value = mock_jira_instance
        mock_comment = MagicMock()
        mock_comment.id = '10001'
        mock_jira_instance.add_comment.return_value = mock_comment

        service = JiraService()
        comment = service.add_comment("PROJECT-123", "This is a test comment.")
        self.assertEqual(comment.id, '10001')
        mock_jira_instance.add_comment.assert_called_once_with("PROJECT-123", "This is a test comment.")

    def test_add_comment_client_not_initialized(self):
        service = JiraService.__new__(JiraService)  # Create instance without calling __init__
        service.client = None
        with self.assertRaises(ValueError) as context:
            service.add_comment("PROJECT-123", "Test comment")
        self.assertIn("Jira client not initialized.", str(context.exception))

    @patch('integrations.services.jira_service.settings')
    @patch('integrations.services.jira_service.JIRA')
    def test_add_comment_empty_comment_skipped(self, mock_jira, mock_settings):
        mock_settings.JIRA_CONFIG = self.valid_jira_config
        mock_jira_instance = MagicMock()
        mock_jira.return_value = mock_jira_instance

        service = JiraService()
        comment = service.add_comment("PROJECT-123", "") # Empty comment
        self.assertIsNone(comment)
        mock_jira_instance.add_comment.assert_not_called()

        comment_whitespace = service.add_comment("PROJECT-123", "   ") # Whitespace comment
        self.assertIsNone(comment_whitespace)
        mock_jira_instance.add_comment.assert_not_called()
        
    @patch('integrations.services.jira_service.settings')
    @patch('integrations.services.jira_service.JIRA')
    def test_add_comment_jira_error(self, mock_jira, mock_settings):
        mock_settings.JIRA_CONFIG = self.valid_jira_config
        mock_jira_instance = MagicMock()
        mock_jira_instance.add_comment.side_effect = JIRAError("Failed to add comment")
        mock_jira.return_value = mock_jira_instance

        service = JiraService()
        with self.assertRaises(JIRAError):
            service.add_comment("PROJECT-123", "Test comment")
        mock_jira_instance.add_comment.assert_called_once_with("PROJECT-123", "Test comment")

    @patch('integrations.services.jira_service.settings')
    @patch('integrations.services.jira_service.JIRA')
    def test_add_comment_connection_error(self, mock_jira, mock_settings):
        mock_settings.JIRA_CONFIG = self.valid_jira_config
        mock_jira_instance = MagicMock()
        mock_jira_instance.add_comment.side_effect = ConnectionError("Connection failed")
        mock_jira.return_value = mock_jira_instance

        service = JiraService()
        with self.assertRaises(ConnectionError):
            service.add_comment("PROJECT-123", "Test comment")
        mock_jira_instance.add_comment.assert_called_once_with("PROJECT-123", "Test comment")

    @patch('integrations.services.jira_service.settings')
    @patch('integrations.services.jira_service.JIRA')
    def test_get_issue_status_category_success(self, mock_jira, mock_settings):
        mock_settings.JIRA_CONFIG = self.valid_jira_config
        mock_jira_instance = MagicMock()
        mock_jira.return_value = mock_jira_instance
        
        mock_issue = MagicMock()
        mock_issue.fields = MagicMock()
        mock_issue.fields.status = MagicMock()
        mock_issue.fields.status.statusCategory = MagicMock()
        mock_issue.fields.status.statusCategory.key = 'done'
        mock_jira_instance.issue.return_value = mock_issue

        service = JiraService()
        status_category = service.get_issue_status_category("PROJECT-123")
        self.assertEqual(status_category, 'done')
        mock_jira_instance.issue.assert_called_once_with("PROJECT-123", fields="status")

    def test_get_issue_status_category_client_not_initialized(self):
        service = JiraService.__new__(JiraService)  # Create instance without calling __init__
        service.client = None
        with self.assertRaises(ValueError) as context:
            service.get_issue_status_category("PROJECT-123")
        self.assertIn("Jira client not initialized.", str(context.exception))

    @patch('integrations.services.jira_service.settings')
    @patch('integrations.services.jira_service.JIRA')
    def test_get_issue_status_category_jira_error(self, mock_jira, mock_settings):
        mock_settings.JIRA_CONFIG = self.valid_jira_config
        mock_jira_instance = MagicMock()
        mock_jira_instance.issue.side_effect = JIRAError("Issue not found")
        mock_jira.return_value = mock_jira_instance

        service = JiraService()
        with self.assertRaises(JIRAError):
            service.get_issue_status_category("PROJECT-123")
        mock_jira_instance.issue.assert_called_once_with("PROJECT-123", fields="status")

    @patch('integrations.services.jira_service.settings')
    @patch('integrations.services.jira_service.JIRA')
    def test_get_issue_status_category_connection_error(self, mock_jira, mock_settings):
        mock_settings.JIRA_CONFIG = self.valid_jira_config
        mock_jira_instance = MagicMock()
        mock_jira_instance.issue.side_effect = ConnectionError("Connection failed")
        mock_jira.return_value = mock_jira_instance

        service = JiraService()
        with self.assertRaises(ConnectionError):
            service.get_issue_status_category("PROJECT-123")
        mock_jira_instance.issue.assert_called_once_with("PROJECT-123", fields="status")

    @patch('integrations.services.jira_service.settings')
    @patch('integrations.services.jira_service.JIRA')
    def test_get_issue_status_category_missing_components(self, mock_jira, mock_settings):
        mock_settings.JIRA_CONFIG = self.valid_jira_config
        mock_jira_instance = MagicMock()
        mock_jira.return_value = mock_jira_instance
        
        # Test case 1: statusCategory is None
        mock_issue_no_status_category = MagicMock()
        mock_issue_no_status_category.fields = MagicMock()
        mock_issue_no_status_category.fields.status = MagicMock()
        mock_issue_no_status_category.fields.status.statusCategory = None
        mock_jira_instance.issue.return_value = mock_issue_no_status_category
        service = JiraService()
        status_category = service.get_issue_status_category("PROJECT-001")
        self.assertIsNone(status_category)
        mock_jira_instance.issue.assert_called_with("PROJECT-001", fields="status")

        # Test case 2: status is None
        mock_issue_no_status = MagicMock()
        mock_issue_no_status.fields = MagicMock()
        mock_issue_no_status.fields.status = None
        mock_jira_instance.issue.return_value = mock_issue_no_status
        status_category = service.get_issue_status_category("PROJECT-002")
        self.assertIsNone(status_category)
        mock_jira_instance.issue.assert_called_with("PROJECT-002", fields="status")

        # Test case 3: fields is None
        mock_issue_no_fields = MagicMock()
        mock_issue_no_fields.fields = None
        mock_jira_instance.issue.return_value = mock_issue_no_fields
        status_category = service.get_issue_status_category("PROJECT-003")
        self.assertIsNone(status_category)
        mock_jira_instance.issue.assert_called_with("PROJECT-003", fields="status")
        
        # Test case 4: statusCategory.key is missing (hasattr check)
        mock_issue_no_key = MagicMock()
        mock_issue_no_key.fields = MagicMock()
        mock_issue_no_key.fields.status = MagicMock()
        mock_issue_no_key.fields.status.statusCategory = MagicMock()
        del mock_issue_no_key.fields.status.statusCategory.key # Remove key attribute
        mock_jira_instance.issue.return_value = mock_issue_no_key
        status_category = service.get_issue_status_category("PROJECT-004")
        self.assertIsNone(status_category)
        mock_jira_instance.issue.assert_called_with("PROJECT-004", fields="status")

    @patch('integrations.services.jira_service.settings')
    @patch('integrations.services.jira_service.JIRA')
    def test_add_watcher_success(self, mock_jira, mock_settings):
        mock_settings.JIRA_CONFIG = self.valid_jira_config
        mock_jira_instance = MagicMock()
        mock_jira.return_value = mock_jira_instance

        service = JiraService()
        service.add_watcher("PROJECT-123", "test_watcher")
        mock_jira_instance.add_watcher.assert_called_once_with("PROJECT-123", "test_watcher")

    def test_add_watcher_client_not_initialized(self):
        service = JiraService.__new__(JiraService)  # Create instance without calling __init__
        service.client = None
        with self.assertRaises(ValueError) as context:
            service.add_watcher("PROJECT-123", "test_watcher")
        self.assertIn("Jira client not initialized.", str(context.exception))

    @patch('integrations.services.jira_service.settings')
    @patch('integrations.services.jira_service.JIRA')
    def test_add_watcher_username_not_provided(self, mock_jira, mock_settings):
        mock_settings.JIRA_CONFIG = self.valid_jira_config
        mock_jira_instance = MagicMock()
        mock_jira.return_value = mock_jira_instance

        service = JiraService()
        service.add_watcher("PROJECT-123", None) # Username not provided
        mock_jira_instance.add_watcher.assert_not_called()
        
        service.add_watcher("PROJECT-123", "") # Username is empty string
        mock_jira_instance.add_watcher.assert_not_called()

        service.add_watcher("PROJECT-123", "  ") # Username is whitespace
        mock_jira_instance.add_watcher.assert_not_called()


    @patch('integrations.services.jira_service.settings')
    @patch('integrations.services.jira_service.JIRA')
    def test_add_watcher_jira_error(self, mock_jira, mock_settings):
        mock_settings.JIRA_CONFIG = self.valid_jira_config
        mock_jira_instance = MagicMock()
        mock_jira_instance.add_watcher.side_effect = JIRAError("Failed to add watcher")
        mock_jira.return_value = mock_jira_instance

        service = JiraService()
        with self.assertRaises(JIRAError):
            service.add_watcher("PROJECT-123", "test_watcher")
        mock_jira_instance.add_watcher.assert_called_once_with("PROJECT-123", "test_watcher")

    @patch('integrations.services.jira_service.settings')
    @patch('integrations.services.jira_service.JIRA')
    def test_add_watcher_connection_error(self, mock_jira, mock_settings):
        mock_settings.JIRA_CONFIG = self.valid_jira_config
        mock_jira_instance = MagicMock()
        mock_jira_instance.add_watcher.side_effect = ConnectionError("Connection failed")
        mock_jira.return_value = mock_jira_instance

        service = JiraService()
        with self.assertRaises(ConnectionError):
            service.add_watcher("PROJECT-123", "test_watcher")
        mock_jira_instance.add_watcher.assert_called_once_with("PROJECT-123", "test_watcher")


from .services.jira_matcher import JiraRuleMatcherService

class JiraRuleMatcherServiceTests(TestCase):
    def setUp(self):
        # Clean up rules before each test
        JiraIntegrationRule.objects.all().delete()

        self.matcher = JiraRuleMatcherService()

        # Common alert labels that can be used and modified by tests
        self.alert_labels_env_prod = {
            "alertname": "HighCPUUsage",
            "severity": "critical",
            "instance": "server1",
            "env": "prod",
            "region": "us-west-1"
        }
        self.alert_labels_env_staging = {
            "alertname": "HighCPUUsage",
            "severity": "warning",
            "instance": "server2",
            "env": "staging",
            "region": "eu-central-1"
        }

    def test_find_matching_rule_no_rules(self):
        """Test that no rule is found when the database is empty."""
        self.assertIsNone(self.matcher.find_matching_rule(self.alert_labels_env_prod))

    def test_find_matching_rule_no_active_rules(self):
        """Test that no rule is found if all rules are inactive."""
        JiraIntegrationRule.objects.create(
            name="Inactive Rule",
            match_criteria={"severity": "critical"},
            jira_project_key="PROJ",
            jira_issue_type="Bug",
            is_active=False
        )
        self.assertIsNone(self.matcher.find_matching_rule(self.alert_labels_env_prod))

    def test_find_matching_rule_multiple_rules_most_specific_wins(self):
        """Test that the rule with more matching criteria keys is chosen."""
        JiraIntegrationRule.objects.create(
            name="Less Specific Rule",
            match_criteria={"severity": "critical"}, # 1 match
            jira_project_key="PROJ",
            jira_issue_type="Bug",
            is_active=True,
            priority=0
        )
        more_specific_rule = JiraIntegrationRule.objects.create(
            name="More Specific Rule",
            match_criteria={"severity": "critical", "env": "prod"}, # 2 matches
            jira_project_key="PROJ",
            jira_issue_type="Bug",
            is_active=True,
            priority=0
        )
        self.assertEqual(self.matcher.find_matching_rule(self.alert_labels_env_prod), more_specific_rule)

    def test_find_matching_rule_multiple_rules_priority_wins_on_tie(self):
        """Test that highest priority wins if specificity is equal."""
        JiraIntegrationRule.objects.create(
            name="Lower Priority Rule",
            match_criteria={"env": "prod", "region": "us-west-1"}, # 2 matches
            jira_project_key="PROJ",
            jira_issue_type="Bug",
            is_active=True,
            priority=0
        )
        higher_priority_rule = JiraIntegrationRule.objects.create(
            name="Higher Priority Rule",
            match_criteria={"severity": "critical", "instance": "server1"}, # 2 matches
            jira_project_key="PROJ",
            jira_issue_type="Bug",
            is_active=True,
            priority=10 # Higher priority
        )
        self.assertEqual(self.matcher.find_matching_rule(self.alert_labels_env_prod), higher_priority_rule)

    def test_find_matching_rule_multiple_rules_name_wins_on_tie_specificity_priority(self):
        """Test that alphabetical name wins if specificity and priority are equal."""
        JiraIntegrationRule.objects.create(
            name="Rule ZZZ", # Later alphabetically
            match_criteria={"env": "prod"},
            jira_project_key="PROJ",
            jira_issue_type="Bug",
            is_active=True,
            priority=5
        )
        alphabetical_rule = JiraIntegrationRule.objects.create(
            name="Rule AAA", # Earlier alphabetically
            match_criteria={"severity": "critical"},
            jira_project_key="PROJ",
            jira_issue_type="Bug",
            is_active=True,
            priority=5
        )
        # alert_labels_env_prod matches both {"env": "prod"} and {"severity": "critical"}
        # with one key each. Both have priority 5. So, "Rule AAA" should win.
        self.assertEqual(self.matcher.find_matching_rule(self.alert_labels_env_prod), alphabetical_rule)
        
        # Test with a different alert that also causes a tie
        alert_staging_critical = {
            "alertname": "DiskFull",
            "severity": "critical", # Matches Rule AAA
            "instance": "db01",
            "env": "staging", # Matches Rule ZZZ if its criteria was {"env": "staging"}
                            # but current Rule ZZZ has {"env": "prod"}
                            # To make this test clearer, let's create a specific setup for it.
        }
        JiraIntegrationRule.objects.all().delete() # Clear previous rules
        rule_b = JiraIntegrationRule.objects.create(
            name="Rule B",
            match_criteria={"severity": "critical"},
            jira_project_key="PROJ", jira_issue_type="Bug", is_active=True, priority=1
        )
        rule_a = JiraIntegrationRule.objects.create(
            name="Rule A",
            match_criteria={"instance": "db01"},
            jira_project_key="PROJ", jira_issue_type="Bug", is_active=True, priority=1
        )
        # alert_staging_critical has "severity": "critical" (matches Rule B) and "instance": "db01" (matches Rule A)
        # Both rules match 1 criterion key, both have priority 1. "Rule A" should win.
        self.assertEqual(self.matcher.find_matching_rule(alert_staging_critical), rule_a)


    def test_find_matching_rule_complex_scenario_specificity_priority_name(self):
        """Test a complex scenario with multiple rules and varying matches."""
        # Order of preference: Specificity > Priority > Name (alphabetical)
        
        # Rules
        rule1_low_spec_low_prio = JiraIntegrationRule.objects.create(
            name="Rule1 LowSpec LowPrio",
            match_criteria={"region": "us-west-1"}, # 1 match with prod alert
            jira_project_key="PROJ1", jira_issue_type="Bug", is_active=True, priority=0
        )
        rule2_med_spec_med_prio = JiraIntegrationRule.objects.create(
            name="Rule2 MedSpec MedPrio",
            match_criteria={"env": "prod", "region": "us-west-1"}, # 2 matches with prod alert
            jira_project_key="PROJ2", jira_issue_type="Task", is_active=True, priority=5
        )
        rule3_med_spec_high_prio_b = JiraIntegrationRule.objects.create(
            name="Rule3 MedSpec HighPrio B_Name", # Name comes after A
            match_criteria={"severity": "critical", "instance": "server1"}, # 2 matches with prod alert
            jira_project_key="PROJ3B", jira_issue_type="Story", is_active=True, priority=10
        )
        rule4_med_spec_high_prio_a = JiraIntegrationRule.objects.create(
            name="Rule4 MedSpec HighPrio A_Name", # Name comes before B
            match_criteria={"alertname": "HighCPUUsage", "env": "prod"}, # 2 matches with prod alert
            jira_project_key="PROJ3A", jira_issue_type="Epic", is_active=True, priority=10
        )
        rule5_high_spec_low_prio = JiraIntegrationRule.objects.create(
            name="Rule5 HighSpec LowPrio",
            match_criteria={"alertname": "HighCPUUsage", "severity": "critical", "env": "prod"}, # 3 matches
            jira_project_key="PROJ4", jira_issue_type="Bug", is_active=True, priority=0
        )
        rule6_inactive = JiraIntegrationRule.objects.create(
            name="Rule6 Inactive HighSpec HighPrio",
            match_criteria={"alertname": "HighCPUUsage", "severity": "critical", "env": "prod", "instance": "server1"}, # 4 matches
            jira_project_key="PROJ5", jira_issue_type="Bug", is_active=False, priority=20
        )

        # Scenario 1: rule5 (highest specificity) should win
        self.assertEqual(self.matcher.find_matching_rule(self.alert_labels_env_prod), rule5_high_spec_low_prio)

        # Modify alert to make rule2, rule3, rule4 have equal highest specificity
        alert_modified_for_prio_name_test = {
            "alertname": "HighCPUUsage", "severity": "critical", "env": "prod", "instance": "server1",
            "custom_label_for_rule3b": "foo", # make rule3b match 2
            "custom_label_for_rule4a": "bar"  # make rule4a match 2
        }
        # Now, for alert_modified_for_prio_name_test:
        # rule1: region (1 match)
        # rule2: env (1 match, because alert has no region) - NO, this is wrong.
        # Let's re-evaluate with self.alert_labels_env_prod which is:
        #  { "alertname": "HighCPUUsage", "severity": "critical", "instance": "server1", "env": "prod", "region": "us-west-1" }
        #
        # rule1 (LowSpec LowPrio): {"region": "us-west-1"} - 1 match (region)
        # rule2 (MedSpec MedPrio): {"env": "prod", "region": "us-west-1"} - 2 matches (env, region)
        # rule3 (MedSpec HighPrio B): {"severity": "critical", "instance": "server1"} - 2 matches (severity, instance)
        # rule4 (MedSpec HighPrio A): {"alertname": "HighCPUUsage", "env": "prod"} - 2 matches (alertname, env)
        # rule5 (HighSpec LowPrio): {"alertname": "HighCPUUsage", "severity": "critical", "env": "prod"} - 3 matches
        # rule6 (Inactive): N/A
        #
        # Winner for self.alert_labels_env_prod is rule5 (3 matches). Correct.

        # Create a new alert where rule3 and rule4 are the top contenders for specificity and priority
        alert_for_prio_name_tie = {
            "alertname": "HighCPUUsage", "severity": "critical", "env": "prod", "instance": "server1",
            # This alert matches rule3 and rule4 with 2 criteria each.
            # Both have priority 10.
            # rule4_med_spec_high_prio_a should win due to name.
        }
        # For alert_for_prio_name_tie:
        # rule1: No match (no region)
        # rule2: env="prod" (1 match)
        # rule3: severity="critical", instance="server1" (2 matches, Prio 10, Name B)
        # rule4: alertname="HighCPUUsage", env="prod" (2 matches, Prio 10, Name A)
        # rule5: alertname, severity, env (3 matches) - NO, rule5 needs all 3, this alert only has 2 of them for rule5 if region missing.
        # Let's re-evaluate rule5 for alert_for_prio_name_tie:
        # rule5: {"alertname": "HighCPUUsage", "severity": "critical", "env": "prod"}
        # alert_for_prio_name_tie has all three. So rule5 has 3 matches (Prio 0).
        # This means rule5 would still win over rule3 and rule4.

        # To test the priority and name tie break properly, we need rules with EQUAL specificity.
        # Let's delete all rules and create a specific scenario.
        JiraIntegrationRule.objects.all().delete()
        
        # Specificity: 2, Priority: 10
        rule_prio10_name_b = JiraIntegrationRule.objects.create(
            name="Rule Prio10 NameB",
            match_criteria={"severity": "critical", "instance": "server1"}, 
            jira_project_key="P10B", jira_issue_type="Bug", is_active=True, priority=10
        )
        # Specificity: 2, Priority: 10
        rule_prio10_name_a = JiraIntegrationRule.objects.create(
            name="Rule Prio10 NameA", # Wins by name
            match_criteria={"alertname": "HighCPUUsage", "env": "prod"},
            jira_project_key="P10A", jira_issue_type="Bug", is_active=True, priority=10
        )
        # Specificity: 2, Priority: 5
        rule_prio5 = JiraIntegrationRule.objects.create(
            name="Rule Prio5",
            match_criteria={"region": "us-west-1", "instance": "server1"}, # region is in prod alert
            jira_project_key="P5", jira_issue_type="Bug", is_active=True, priority=5
        )
        # Specificity: 3 (should win overall)
        rule_spec3 = JiraIntegrationRule.objects.create(
            name="Rule Spec3",
            match_criteria={"alertname": "HighCPUUsage", "severity": "critical", "env": "prod"},
            jira_project_key="S3", jira_issue_type="Bug", is_active=True, priority=0
        )

        # Using self.alert_labels_env_prod:
        #   "alertname": "HighCPUUsage", "severity": "critical", "instance": "server1", "env": "prod", "region": "us-west-1"
        # rule_prio10_name_b: {"severity", "instance"} -> 2 matches. Prio 10.
        # rule_prio10_name_a: {"alertname", "env"} -> 2 matches. Prio 10.
        # rule_prio5: {"region", "instance"} -> 2 matches. Prio 5.
        # rule_spec3: {"alertname", "severity", "env"} -> 3 matches. Prio 0.
        # Expected: rule_spec3 (most specific)
        self.assertEqual(self.matcher.find_matching_rule(self.alert_labels_env_prod), rule_spec3)

        # Now, let's use an alert that makes Prio10 rules the most specific.
        alert_for_prio_name_test_2 = {
            "alertname": "HighCPUUsage", "severity": "critical", "instance": "server1", "env": "prod"
            # No "region", so rule_prio5 only gets 1 match (instance)
            # rule_spec3 gets 3 matches.
            # rule_prio10_name_b gets 2 matches.
            # rule_prio10_name_a gets 2 matches.
            # rule_spec3 still wins.
        }
        self.assertEqual(self.matcher.find_matching_rule(alert_for_prio_name_test_2), rule_spec3)

        # To test the prio/name tie break, we need to remove/change rule_spec3
        rule_spec3.is_active = False
        rule_spec3.save()

        # Now, for alert_for_prio_name_test_2 (and self.alert_labels_env_prod if we ignore region for rule_prio5):
        # rule_prio10_name_b: {"severity", "instance"} -> 2 matches. Prio 10.
        # rule_prio10_name_a: {"alertname", "env"} -> 2 matches. Prio 10.
        # rule_prio5: {"instance"} -> 1 match (for alert_for_prio_name_test_2), or {"region", "instance"} -> 2 matches (for self.alert_labels_env_prod)
        
        # Using alert_for_prio_name_test_2 (rule_prio5 has 1 match):
        # Top contenders are rule_prio10_name_a and rule_prio10_name_b (both 2 matches, prio 10)
        # Expected: rule_prio10_name_a (alphabetical)
        self.assertEqual(self.matcher.find_matching_rule(alert_for_prio_name_test_2), rule_prio10_name_a)

        # Using self.alert_labels_env_prod (rule_prio5 has 2 matches, but lower priority):
        # Top contenders are rule_prio10_name_a and rule_prio10_name_b (both 2 matches, prio 10)
        # rule_prio5 also has 2 matches, but prio 5, so it's out.
        # Expected: rule_prio10_name_a (alphabetical)
        self.assertEqual(self.matcher.find_matching_rule(self.alert_labels_env_prod), rule_prio10_name_a)


    def test_find_matching_rule_no_match_for_alert(self):
        """Test that no rule is found if alert labels don't match any active rules."""
        JiraIntegrationRule.objects.create(
            name="Prod Critical Rule",
            match_criteria={"env": "prod", "severity": "critical"},
            jira_project_key="PROJ", jira_issue_type="Bug", is_active=True
        )
        # self.alert_labels_env_staging is {"severity": "warning", "env": "staging"}
        self.assertIsNone(self.matcher.find_matching_rule(self.alert_labels_env_staging))

    # Tests for _does_rule_match (indirectly through find_matching_rule, but adding some direct ones for clarity)
    def test_does_rule_match_positive_match(self):
        rule = JiraIntegrationRule(match_criteria={"severity": "critical", "env": "prod"})
        self.assertTrue(self.matcher._does_rule_match(rule, self.alert_labels_env_prod))

    def test_does_rule_match_negative_mismatch(self):
        rule = JiraIntegrationRule(match_criteria={"severity": "warning"})
        self.assertFalse(self.matcher._does_rule_match(rule, self.alert_labels_env_prod))

    def test_does_rule_match_empty_criteria_for_rule(self):
        rule = JiraIntegrationRule(match_criteria={}) # Empty criteria on rule
        self.assertFalse(self.matcher._does_rule_match(rule, self.alert_labels_env_prod))
        
    def test_does_rule_match_criteria_key_not_in_alert(self):
        rule = JiraIntegrationRule(match_criteria={"custom_key": "value"})
        self.assertFalse(self.matcher._does_rule_match(rule, self.alert_labels_env_prod))

    # Tests for _does_criteria_match (implicitly tested, but good for direct verification)
    def test_does_criteria_match_full_match(self):
        criteria = {"severity": "critical", "env": "prod"}
        self.assertTrue(self.matcher._does_criteria_match(criteria, self.alert_labels_env_prod))

    def test_does_criteria_match_partial_mismatch_value(self):
        criteria = {"severity": "critical", "env": "staging"} # env value mismatch
        self.assertFalse(self.matcher._does_criteria_match(criteria, self.alert_labels_env_prod))

    def test_does_criteria_match_key_not_in_alert(self):
        criteria = {"custom_key": "value"}
        self.assertFalse(self.matcher._does_criteria_match(criteria, self.alert_labels_env_prod))

    def test_does_criteria_match_alert_has_extra_keys(self):
        criteria = {"severity": "critical"} # Alert has more keys (env, instance, region)
        self.assertTrue(self.matcher._does_criteria_match(criteria, self.alert_labels_env_prod))

    def test_does_criteria_match_empty_criteria(self):
        # As per current _does_criteria_match, empty criteria means a match ( vacuously true).
        # However, _does_rule_match prevents rules with empty criteria from matching.
        self.assertTrue(self.matcher._does_criteria_match({}, self.alert_labels_env_prod))
        self.assertTrue(self.matcher._does_criteria_match({}, {})) # Empty criteria vs empty labels

    def test_does_criteria_match_criteria_subset_of_alert(self):
        criteria = {"env": "prod", "region": "us-west-1"}
        alert = {"env": "prod", "region": "us-west-1", "severity": "critical"}
        self.assertTrue(self.matcher._does_criteria_match(criteria, alert))

    def test_does_criteria_match_alert_subset_of_criteria(self):
        criteria = {"env": "prod", "region": "us-west-1", "severity": "critical"}
        alert = {"env": "prod", "region": "us-west-1"}
        self.assertFalse(self.matcher._does_criteria_match(criteria, alert)) # Fails because 'severity' is missing in alert

    def test_does_criteria_match_no_common_keys(self):
        criteria = {"team": "backend"}
        alert = {"service": "frontend"}
        self.assertFalse(self.matcher._does_criteria_match(criteria, alert))

    def test_find_matching_rule_single_active_rule_matches(self):
        """Test finding a single active rule that matches."""
        rule = JiraIntegrationRule.objects.create(
            name="Matching Rule",
            match_criteria={"severity": "critical", "env": "prod"},
            jira_project_key="PROJ",
            jira_issue_type="Bug",
            is_active=True
        )
        self.assertEqual(self.matcher.find_matching_rule(self.alert_labels_env_prod), rule)

    def test_find_matching_rule_single_active_rule_no_match(self):
        """Test that a non-matching single active rule is not found."""
        JiraIntegrationRule.objects.create(
            name="Non-Matching Rule",
            match_criteria={"severity": "warning"}, # Mismatch with alert_labels_env_prod
            jira_project_key="PROJ",
            jira_issue_type="Bug",
            is_active=True
        )
        self.assertIsNone(self.matcher.find_matching_rule(self.alert_labels_env_prod))

    def test_find_matching_rule_single_active_rule_empty_criteria(self):
        """Test that a rule with empty match_criteria does not match."""
        JiraIntegrationRule.objects.create(
            name="Empty Criteria Rule",
            match_criteria={}, # Empty criteria
            jira_project_key="PROJ",
            jira_issue_type="Bug",
            is_active=True
        )
        self.assertIsNone(self.matcher.find_matching_rule(self.alert_labels_env_prod))
