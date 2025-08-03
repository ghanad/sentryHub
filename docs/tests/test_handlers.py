from django.test import TestCase
from unittest.mock import patch
from alerts.models import AlertGroup
from alerts.signals import alert_processed

class HandleDocumentationMatchingTest(TestCase):
    @patch('docs.handlers.match_documentation_to_alert')
    def test_calls_matcher_with_alert_group(self, mock_match):
        alert = AlertGroup.objects.create(
            fingerprint='fp', name='Alert', labels={},
            severity='critical', current_status='firing'
        )
        alert_processed.send(sender=None, alert_group=alert, instance=None, status='firing')
        mock_match.assert_called_once_with(alert)

    @patch('docs.handlers.logger')
    def test_logs_warning_when_no_alert_group(self, mock_logger):
        alert_processed.send(sender=None, alert_group=None, instance=None, status='firing')
        mock_logger.warning.assert_called()
