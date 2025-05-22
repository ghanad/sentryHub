# integrations/tests/test_jira_matcher.py

import unittest
from unittest.mock import patch, MagicMock
from django.test import TestCase

# Import the service and model (will be mocked)
from integrations.services.jira_matcher import JiraRuleMatcherService
from integrations.models import JiraIntegrationRule # Will be mocked

class JiraRuleMatcherServiceTests(TestCase):

    def setUp(self):
        # Instantiate the service for each test
        self.matcher_service = JiraRuleMatcherService()

    def test_does_criteria_match_success(self):
        """Test _does_criteria_match with matching criteria."""
        criteria = {"severity": "critical", "env": "prod"}
        alert_labels = {"severity": "critical", "env": "prod", "alertname": "HighLatency"}
        self.assertTrue(self.matcher_service._does_criteria_match(criteria, alert_labels))

    def test_does_criteria_match_missing_label(self):
        """Test _does_criteria_match when a required label is missing in alert labels."""
        criteria = {"severity": "critical", "env": "prod"}
        alert_labels = {"severity": "critical", "alertname": "HighLatency"} # Missing 'env'
        self.assertFalse(self.matcher_service._does_criteria_match(criteria, alert_labels))

    def test_does_criteria_match_value_mismatch(self):
        """Test _does_criteria_match when a label value does not match."""
        criteria = {"severity": "critical", "env": "prod"}
        alert_labels = {"severity": "critical", "env": "dev", "alertname": "HighLatency"} # 'env' mismatch
        self.assertFalse(self.matcher_service._does_criteria_match(criteria, alert_labels))

    def test_does_criteria_match_empty_criteria(self):
        """Test _does_criteria_match with an empty criteria dictionary."""
        criteria = {}
        alert_labels = {"severity": "critical", "env": "prod"}
        # An empty criteria dictionary should match any alert labels
        self.assertTrue(self.matcher_service._does_criteria_match(criteria, alert_labels))

    def test_does_criteria_match_criteria_subset_of_labels(self):
        """Test _does_criteria_match when criteria is a subset of alert labels."""
        criteria = {"severity": "critical"}
        alert_labels = {"severity": "critical", "env": "prod", "alertname": "HighLatency"}
        self.assertTrue(self.matcher_service._does_criteria_match(criteria, alert_labels))

    def test_does_criteria_match_label_value_type_conversion(self):
        """Test _does_criteria_match handles different value types by converting to string."""
        criteria = {"count": 5} # Integer in criteria
        alert_labels = {"count": "5", "status": "firing"} # String in labels
        self.assertTrue(self.matcher_service._does_criteria_match(criteria, alert_labels))

        criteria = {"is_active": True} # Boolean in criteria
        alert_labels = {"is_active": "True", "status": "firing"} # String in labels
        self.assertTrue(self.matcher_service._does_criteria_match(criteria, alert_labels))

    @patch('integrations.services.jira_matcher.JiraRuleMatcherService._does_criteria_match')
    def test_does_rule_match_success(self, mock_does_criteria_match):
        """Test _does_rule_match when criteria match."""
        mock_rule = MagicMock()
        mock_rule.match_criteria = {"severity": "critical"}
        alert_labels = {"severity": "critical", "env": "prod"}

        mock_does_criteria_match.return_value = True

        self.assertTrue(self.matcher_service._does_rule_match(mock_rule, alert_labels))
        mock_does_criteria_match.assert_called_once_with(mock_rule.match_criteria, alert_labels)

    @patch('integrations.services.jira_matcher.JiraRuleMatcherService._does_criteria_match')
    def test_does_rule_match_no_criteria(self, mock_does_criteria_match):
        """Test _does_rule_match when rule has no match criteria."""
        mock_rule = MagicMock()
        mock_rule.match_criteria = None # No criteria defined
        alert_labels = {"severity": "critical", "env": "prod"}

        self.assertFalse(self.matcher_service._does_rule_match(mock_rule, alert_labels))
        mock_does_criteria_match.assert_not_called()

    @patch('integrations.services.jira_matcher.JiraRuleMatcherService._does_criteria_match')
    def test_does_rule_match_criteria_no_match(self, mock_does_criteria_match):
        """Test _does_rule_match when criteria do not match."""
        mock_rule = MagicMock()
        mock_rule.match_criteria = {"severity": "critical"}
        alert_labels = {"severity": "warning", "env": "prod"}

        mock_does_criteria_match.return_value = False

        self.assertFalse(self.matcher_service._does_rule_match(mock_rule, alert_labels))
        mock_does_criteria_match.assert_called_once_with(mock_rule.match_criteria, alert_labels)

    @patch('integrations.services.jira_matcher.JiraIntegrationRule.objects')
    @patch('integrations.services.jira_matcher.JiraRuleMatcherService._does_rule_match')
    def test_find_matching_rule_no_active_rules(self, mock_does_rule_match, mock_objects):
        """Test find_matching_rule when there are no active rules."""
        # Mock the filter method to return an iterable MagicMock
        mock_queryset = MagicMock()
        mock_queryset.__iter__.return_value = iter([]) # Make it iterable
        mock_objects.filter.return_value = mock_queryset

        alert_labels = {"severity": "critical", "env": "prod"}
        best_match = self.matcher_service.find_matching_rule(alert_labels)

        mock_objects.filter.assert_called_once_with(is_active=True)
        mock_does_rule_match.assert_not_called()
        self.assertIsNone(best_match)

    @patch('integrations.services.jira_matcher.JiraIntegrationRule.objects')
    @patch('integrations.services.jira_matcher.JiraRuleMatcherService._does_rule_match')
    def test_find_matching_rule_no_rules_match(self, mock_does_rule_match, mock_objects):
        """Test find_matching_rule when active rules exist but none match."""
        mock_rule1 = ComparableRuleMock(name="Rule1", id=1, match_criteria={"severity": "warning"}, priority=1)
        mock_rule2 = ComparableRuleMock(name="Rule2", id=2, match_criteria={"env": "dev"}, priority=1)
        # Mock the filter method to return an iterable MagicMock
        mock_queryset = MagicMock()
        mock_queryset.__iter__.return_value = iter([mock_rule1, mock_rule2]) # Make it iterable
        mock_objects.filter.return_value = mock_queryset

        mock_does_rule_match.return_value = False # Simulate no match

        alert_labels = {"severity": "critical", "env": "prod"}
        best_match = self.matcher_service.find_matching_rule(alert_labels)

        mock_objects.filter.assert_called_once_with(is_active=True)
        self.assertEqual(mock_does_rule_match.call_count, 2) # Called for each rule
        self.assertIsNone(best_match)

    @patch('integrations.services.jira_matcher.JiraIntegrationRule.objects')
    @patch('integrations.services.jira_matcher.JiraRuleMatcherService._does_rule_match')
    def test_find_matching_rule_one_rule_matches(self, mock_does_rule_match, mock_objects):
        """Test find_matching_rule when only one rule matches."""
        mock_rule1 = ComparableRuleMock(name="Rule1", id=1, match_criteria={"severity": "critical"}, priority=1)
        mock_rule2 = ComparableRuleMock(name="Rule2", id=2, match_criteria={"env": "dev"}, priority=1)
        # Mock the filter method to return an iterable MagicMock
        mock_queryset = MagicMock()
        mock_queryset.__iter__.return_value = iter([mock_rule1, mock_rule2]) # Make it iterable
        mock_objects.filter.return_value = mock_queryset

        # Simulate only rule1 matching
        def side_effect_does_rule_match(rule, labels):
            return rule == mock_rule1
        mock_does_rule_match.side_effect = side_effect_does_rule_match

        alert_labels = {"severity": "critical", "env": "prod"}
        best_match = self.matcher_service.find_matching_rule(alert_labels)

        mock_objects.filter.assert_called_once_with(is_active=True)
        self.assertEqual(mock_does_rule_match.call_count, 2) # Called for each rule
        self.assertEqual(best_match, mock_rule1)

    @patch('integrations.services.jira_matcher.JiraIntegrationRule.objects')
    @patch('integrations.services.jira_matcher.JiraRuleMatcherService._does_rule_match')
    def test_find_matching_rule_multiple_rules_match_sorting(self, mock_does_rule_match, mock_objects):
        """Test find_matching_rule with multiple matching rules, verifying sorting."""
        # Rules with different specificity, priority, and name for sorting test
        # Specificity (criteria count), Priority (desc), Name (asc)
# Define a simple class to act as a comparable mock for JiraIntegrationRule
class ComparableRuleMock:
    def __init__(self, name, id, match_criteria, priority):
        self.name = name
        self.id = id
        self.match_criteria = match_criteria
        self.priority = priority

    # Implement __lt__ for comparison based on the sorting key logic in find_matching_rule
    def __lt__(self, other):
        return (
            -len(self.match_criteria or {}), -self.priority, self.name
        ) < (
            -len(other.match_criteria or {}), -other.priority, other.name
        )

# ... rest of the tests ...

        # Rules with different specificity, priority, and name for sorting test
        # Specificity (criteria count), Priority (desc), Name (asc)
        # Rules with different specificity, priority, and name for sorting test
        # Specificity (criteria count), Priority (desc), Name (asc)
        mock_rule_low_spec_high_prio_a = ComparableRuleMock(name="Rule A", id=1, match_criteria={"severity": "critical"}, priority=10) # Spec 1, Prio 10, Name A
        mock_rule_high_spec_low_prio_b = ComparableRuleMock(name="Rule B", id=2, match_criteria={"severity": "critical", "env": "prod"}, priority=5) # Spec 2, Prio 5, Name B
        mock_rule_low_spec_high_prio_c = ComparableRuleMock(name="Rule C", id=3, match_criteria={"severity": "critical"}, priority=10) # Spec 1, Prio 10, Name C
        mock_rule_high_spec_high_prio_d = ComparableRuleMock(name="Rule D", id=4, match_criteria={"severity": "critical", "env": "prod", "region": "us-east-1"}, priority=10) # Spec 3, Prio 10, Name D

        # Order in the queryset shouldn't matter for the final result due to sorting
        all_rules = [
            mock_rule_low_spec_high_prio_a,
            mock_rule_high_spec_low_prio_b,
            mock_rule_low_spec_high_prio_c,
            mock_rule_high_spec_high_prio_d,
        ]
        # Mock the filter method to return an iterable MagicMock
        mock_queryset = MagicMock()
        mock_queryset.__iter__.return_value = iter(all_rules) # Make it iterable
        mock_objects.filter.return_value = mock_queryset

        # Simulate all rules matching
        mock_does_rule_match.return_value = True

        alert_labels = {"severity": "critical", "env": "prod", "region": "us-east-1", "alertname": "TestAlert"}
        best_match = self.matcher_service.find_matching_rule(alert_labels)

        mock_objects.filter.assert_called_once_with(is_active=True)
        self.assertEqual(mock_does_rule_match.call_count, len(all_rules)) # Called for each rule

        # Expected sorting order:
        # 1. mock_rule_high_spec_high_prio_d (Spec 3)
        # 2. mock_rule_high_spec_low_prio_b (Spec 2)
        # 3. mock_rule_low_spec_high_prio_a (Spec 1, Prio 10, Name A)
        # 4. mock_rule_low_spec_high_prio_c (Spec 1, Prio 10, Name C) - Name A comes before C

        # The best match should be the one with the highest specificity
        self.assertEqual(best_match, mock_rule_high_spec_high_prio_d)

    @patch('integrations.services.jira_matcher.JiraIntegrationRule.objects')
    @patch('integrations.services.jira_matcher.JiraRuleMatcherService._does_rule_match')
    def test_find_matching_rule_sorting_tie_breaker_priority(self, mock_does_rule_match, mock_objects):
        """Test find_matching_rule sorting tie-breaker by priority."""
        # Rules with same specificity, different priority
        mock_rule_prio_low = ComparableRuleMock(name="Rule Low Prio", id=1, match_criteria={"severity": "critical"}, priority=5)
        mock_rule_prio_high = ComparableRuleMock(name="Rule High Prio", id=2, match_criteria={"severity": "critical"}, priority=10)

        all_rules = [mock_rule_prio_low, mock_rule_prio_high]
        # Mock the filter method to return an iterable MagicMock
        mock_queryset = MagicMock()
        mock_queryset.__iter__.return_value = iter(all_rules) # Make it iterable
        mock_objects.filter.return_value = mock_queryset
        mock_does_rule_match.return_value = True

        alert_labels = {"severity": "critical"}
        best_match = self.matcher_service.find_matching_rule(alert_labels)

        self.assertEqual(best_match, mock_rule_prio_high) # High priority should win

    @patch('integrations.services.jira_matcher.JiraIntegrationRule.objects')
    @patch('integrations.services.jira_matcher.JiraRuleMatcherService._does_rule_match')
    def test_find_matching_rule_sorting_tie_breaker_name(self, mock_does_rule_match, mock_objects):
        """Test find_matching_rule sorting tie-breaker by name."""
        # Rules with same specificity and priority, different name
        mock_rule_name_a = ComparableRuleMock(name="Rule A", id=1, match_criteria={"severity": "critical"}, priority=10)
        mock_rule_name_b = ComparableRuleMock(name="Rule B", id=2, match_criteria={"severity": "critical"}, priority=10)

        all_rules = [mock_rule_name_b, mock_rule_name_a] # Order in list shouldn't matter
        # Mock the filter method to return an iterable MagicMock
        mock_queryset = MagicMock()
        mock_queryset.__iter__.return_value = iter(all_rules) # Make it iterable
        mock_objects.filter.return_value = mock_queryset
        mock_does_rule_match.return_value = True

        alert_labels = {"severity": "critical"}
        best_match = self.matcher_service.find_matching_rule(alert_labels)

        self.assertEqual(best_match, mock_rule_name_a) # Alphabetical name should win