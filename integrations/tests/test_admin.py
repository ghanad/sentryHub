import json
from unittest.mock import MagicMock, patch
from django.test import TestCase
from django.contrib.admin.sites import AdminSite
from django.utils.html import format_html
from django.utils.safestring import SafeString

from integrations.admin import JiraIntegrationRuleAdmin
from integrations.models import JiraIntegrationRule

class JiraIntegrationRuleAdminTest(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = JiraIntegrationRuleAdmin(JiraIntegrationRule, self.site)
        
        # Create a mock JiraIntegrationRule object
        self.rule = MagicMock()
        self.rule.match_criteria = {} # Default to empty dict

    def test_get_match_criteria_preview_valid_json(self):
        """Test get_match_criteria_preview with valid JSON."""
        self.rule.match_criteria = {"job": "node", "severity": "critical"}
        result = self.admin.get_match_criteria_preview(self.rule)
        expected_json = json.dumps(self.rule.match_criteria, indent=2, ensure_ascii=False)
        expected_html = format_html('<pre style="white-space: pre-wrap; max-width: 400px;">{}</pre>', expected_json)
        self.assertIsInstance(result, SafeString)
        self.assertEqual(str(result), str(expected_html))

    def test_get_match_criteria_preview_empty_json(self):
        """Test get_match_criteria_preview with empty JSON."""
        self.rule.match_criteria = {}
        result = self.admin.get_match_criteria_preview(self.rule)
        expected_json = json.dumps(self.rule.match_criteria, indent=2, ensure_ascii=False)
        expected_html = format_html('<pre style="white-space: pre-wrap; max-width: 400px;">{}</pre>', expected_json)
        self.assertIsInstance(result, SafeString)
        self.assertEqual(str(result), str(expected_html))

    def test_get_match_criteria_preview_invalid_json(self):
        """Test get_match_criteria_preview with invalid match_criteria (non-dict)."""
        # Simulate a scenario where match_criteria is not a dictionary
        # Although the model's clean method should prevent this, the admin method should handle it gracefully.
        self.rule.match_criteria = "invalid_json_string" 
        result = self.admin.get_match_criteria_preview(self.rule)
        self.assertEqual(result, "Invalid JSON")

    def test_get_match_criteria_preview_short_description(self):
        """Test that get_match_criteria_preview has proper short description."""
        self.assertEqual(self.admin.get_match_criteria_preview.short_description, "Match Criteria Preview")