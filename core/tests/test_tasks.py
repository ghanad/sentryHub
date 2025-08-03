from django.test import TestCase
from django.test.utils import override_settings
from unittest.mock import patch
from core.tasks import flush_metrics_to_file


class FlushMetricsTaskTests(TestCase):
    def test_flush_metrics_calls_write_when_enabled(self):
        with override_settings(METRICS_ENABLED=True):
            with patch('core.tasks.metrics_manager') as mock_manager:
                flush_metrics_to_file()
                mock_manager.write_metrics.assert_called_once_with()

    def test_flush_metrics_skips_when_disabled(self):
        with override_settings(METRICS_ENABLED=False):
            with patch('core.tasks.metrics_manager') as mock_manager:
                flush_metrics_to_file()
                mock_manager.write_metrics.assert_not_called()
