from django.test import SimpleTestCase
from integrations.services.slack_service import SlackService


class SlackServiceNormalizeChannelTests(SimpleTestCase):
    def setUp(self):
        self.service = SlackService()

    def test_normalize_channel_behaviour_per_implementation(self):
        # Keeps channels that already start with '#'
        self.assertEqual(self.service._normalize_channel('#general'), '#general')
        # Adds '#' when no special prefix; trims whitespace
        self.assertEqual(self.service._normalize_channel('devops'), '#devops')
        self.assertEqual(self.service._normalize_channel('  devops  '), '#devops')
        # Leaves Slack-like IDs untouched
        self.assertEqual(self.service._normalize_channel('C123ABC'), 'C123ABC')
        self.assertEqual(self.service._normalize_channel('G456DEF'), 'G456DEF')
        self.assertEqual(self.service._normalize_channel('U789HIJ'), 'U789HIJ')
        self.assertEqual(self.service._normalize_channel('D000XYZ'), 'D000XYZ')
        # Does not strip '@' per current implementation; will prefix with '#'
        self.assertEqual(self.service._normalize_channel('@alerts'), '#@alerts')
        # Falsy input returns as-is (empty string)
        self.assertEqual(self.service._normalize_channel(''), '')
        # Whitespace-only input triggers IndexError in current implementation (ch[0] access),
        # so we assert that calling it raises IndexError to reflect current behavior.
        with self.assertRaises(IndexError):
            self.service._normalize_channel('   ')