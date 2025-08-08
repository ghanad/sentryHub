from django.test import TestCase, override_settings
from core.services.metrics import metrics_manager
import tempfile
import os


class MetricManagerTests(TestCase):
    def setUp(self):
        # Clear metrics before each test to ensure isolation
        metrics_manager.counters.clear()
        metrics_manager.gauges.clear()

    def test_inc_counter_increments_value(self):
        """Test that inc_counter correctly increments a counter."""
        with override_settings(METRICS_ENABLED=True):
            metrics_manager.inc_counter("test_requests_total", {"method": "GET"})
            metrics_manager.inc_counter("test_requests_total", {"method": "GET"}, value=2)
            metrics_manager.inc_counter("test_errors_total")

        # Check internal state
        self.assertEqual(metrics_manager.counters["test_requests_total"]['method="GET"'], 3)
        self.assertEqual(metrics_manager.counters["test_errors_total"][""], 1)

    def test_set_gauge_sets_value(self):
        """Test that set_gauge correctly sets a gauge's value."""
        with override_settings(METRICS_ENABLED=True):
            metrics_manager.set_gauge("test_queue_size", value=15.5, labels={"queue": "default"})
            metrics_manager.set_gauge("test_temperature", value=25)

        # Check internal state
        self.assertEqual(metrics_manager.gauges["test_queue_size"]['queue="default"'], 15.5)
        self.assertEqual(metrics_manager.gauges["test_temperature"][""], 25)

    def test_format_labels_is_correct(self):
        """Test the internal _format_labels method."""
        labels = {"c": 3, "a": 1, "b": 2}
        formatted = metrics_manager._format_labels(labels)
        # Should be sorted alphabetically by key
        self.assertEqual(formatted, 'a="1",b="2",c="3"')
    
    def test_metrics_disabled_does_nothing(self):
        """Test that no metrics are recorded when METRICS_ENABLED is False."""
        with override_settings(METRICS_ENABLED=False):
            metrics_manager.inc_counter("should_not_exist")
            metrics_manager.set_gauge("should_not_exist_gauge", value=10)
        
        self.assertEqual(len(metrics_manager.counters), 0)
        self.assertEqual(len(metrics_manager.gauges), 0)

    @override_settings(METRICS_ENABLED=True)
    def test_write_metrics_creates_file_with_correct_format(self):
        """Test that write_metrics produces a correctly formatted Prometheus text file."""
        metrics_manager.inc_counter("http_requests_total", {"method": "post", "code": "200"}, 5)
        metrics_manager.inc_counter("http_requests_total", {"method": "get", "code": "200"}, 10)
        metrics_manager.set_gauge("users_online", value=123, labels={"shard": "eu-west-1"})

        with tempfile.TemporaryDirectory() as tmpdir:
            metrics_file = os.path.join(tmpdir, "test.prom")
            with override_settings(METRICS_FILE_PATH=metrics_file):
                metrics_manager.write_metrics()

                self.assertTrue(os.path.exists(metrics_file))
                with open(metrics_file, 'r') as f:
                    content = f.read()

                # Check for correct Prometheus format
                self.assertIn("# TYPE http_requests_total counter", content)
                self.assertIn('http_requests_total{code="200",method="post"} 5', content)
                self.assertIn('http_requests_total{code="200",method="get"} 10', content)
                
                self.assertIn("# TYPE users_online gauge", content)
                self.assertIn('users_online{shard="eu-west-1"} 123', content)

                self.assertIn("# TYPE sentryhub_last_metrics_write_timestamp gauge", content)
                self.assertIn("sentryhub_last_metrics_write_timestamp", content)