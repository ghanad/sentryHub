from django.test import TestCase
from django.test.utils import override_settings
from core.services.metrics import metrics_manager
import tempfile
import os


class MetricManagerTests(TestCase):
    def setUp(self):
        metrics_manager.counters.clear()
        metrics_manager.gauges.clear()

    def test_write_metrics_writes_counters_and_gauges(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "metrics.prom")
            with override_settings(METRICS_ENABLED=True, METRICS_FILE_PATH=path):
                metrics_manager.inc_counter("requests_total", {"method": "GET"}, 2)
                metrics_manager.inc_counter("errors_total")
                metrics_manager.set_gauge("queue_size", {"name": "default"}, 5.5)
                metrics_manager.write_metrics()

            with open(path) as f:
                content = f.read()

        self.assertIn("# TYPE requests_total counter", content)
        self.assertIn('requests_total{method="GET"} 2', content)
        self.assertIn("# TYPE errors_total counter", content)
        self.assertIn("errors_total 1", content)
        self.assertIn("# TYPE queue_size gauge", content)
        self.assertIn('queue_size{name="default"} 5.5', content)
        self.assertIn("sentryhub_last_metrics_write_timestamp", content)

    def test_metrics_disabled_skips_updates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "metrics.prom")
            with override_settings(METRICS_ENABLED=False, METRICS_FILE_PATH=path):
                metrics_manager.inc_counter("requests_total")
                metrics_manager.set_gauge("queue_size", value=3)
                metrics_manager.write_metrics()

            self.assertFalse(os.path.exists(path))
            self.assertEqual(len(metrics_manager.counters), 0)
            self.assertEqual(len(metrics_manager.gauges), 0)
