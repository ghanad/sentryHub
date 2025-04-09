import pytest
from unittest.mock import patch
from alerts.services.alerts_processor import process_alert, resolve_alert
from alerts.models import Alert, AlertGroup, AlertInstance
from django.utils import timezone


@pytest.mark.django_db
class TestAlertsProcessor:
    @patch('alerts.consumers.AlertConsumer.send_alert_update')
    def test_process_alert_create_new_alert(self, mock_send_alert_update):
        alert_data = {
            "job": "test_job",
            "cluster": "test_cluster",
            "description": "Test Alert",
            "severity": "warning",
            "start_time": timezone.now(),
            "end_time": timezone.now(),
        }
        process_alert(alert_data)
        assert Alert.objects.count() == 1
        assert AlertInstance.objects.count() == 1
        mock_send_alert_update.assert_called_once()

    @patch('alerts.consumers.AlertConsumer.send_alert_update')
    def test_process_alert_update_existing_alert(self, mock_send_alert_update):
        alert_data = {
            "job": "test_job",
            "cluster": "test_cluster",
            "description": "Test Alert",
            "severity": "warning",
            "start_time": timezone.now(),
            "end_time": timezone.now(),
        }
        process_alert(alert_data)
        alert_data["severity"] = "critical"
        process_alert(alert_data)

        assert Alert.objects.count() == 1
        assert AlertInstance.objects.count() == 2
        mock_send_alert_update.assert_called()

    @patch('alerts.consumers.AlertConsumer.send_alert_update')
    def test_resolve_alert_existing_alert(self, mock_send_alert_update):
        alert_data = {
            "job": "test_job",
            "cluster": "test_cluster",
            "description": "Test Alert",
            "severity": "warning",
            "start_time": timezone.now(),
            "end_time": timezone.now(),
        }
        process_alert(alert_data)

        alert = Alert.objects.first()
        resolve_alert(alert.job, alert.cluster)
        assert Alert.objects.count() == 0
        mock_send_alert_update.assert_called_once()

    def test_resolve_alert_non_existing_alert(self):
        resolve_alert("non_existing_job", "non_existing_cluster")
        assert Alert.objects.count() == 0