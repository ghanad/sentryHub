from django.core.exceptions import ValidationError
from django.test import TestCase
from integrations.models import SlackIntegrationRule


class SlackIntegrationRuleModelTests(TestCase):
    def test_str_representation_and_defaults(self):
        rule = SlackIntegrationRule.objects.create(
            name="rule1",
            slack_channel="#general",
            match_criteria={},
        )
        self.assertEqual(str(rule), "rule1 (Active, Prio: 0)")
        self.assertTrue(rule.is_active)
        self.assertEqual(rule.priority, 0)

    def test_match_criteria_must_be_dict(self):
        rule = SlackIntegrationRule(
            name="rule2",
            slack_channel="#general",
            match_criteria="not a dict",
        )
        with self.assertRaises(ValidationError):
            rule.full_clean()

    def test_ordering_by_priority_then_name(self):
        r1 = SlackIntegrationRule.objects.create(
            name="b",
            slack_channel="#a",
            match_criteria={},
            priority=1,
        )
        r2 = SlackIntegrationRule.objects.create(
            name="a",
            slack_channel="#a",
            match_criteria={},
            priority=2,
        )
        r3 = SlackIntegrationRule.objects.create(
            name="c",
            slack_channel="#a",
            match_criteria={},
            priority=1,
        )
        rules = list(SlackIntegrationRule.objects.all())
        self.assertEqual(rules, [r2, r1, r3])
