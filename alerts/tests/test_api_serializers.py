from django.test import TestCase
from alerts.models import AlertInstance, AlertGroup
from alerts.api.serializers import AlertInstanceSerializer
from datetime import datetime
from django.utils import timezone
from unittest.mock import MagicMock

class AlertInstanceSerializerTest(TestCase):
    def setUp(self):
        self.alert_group = AlertGroup.objects.create(
            fingerprint="test_fingerprint_1",
            name="Test Alert Group",
            labels={"severity": "critical"},
            severity="critical",
            first_occurrence=timezone.make_aware(datetime(2023, 1, 1, 10, 0, 0)),
            last_occurrence=timezone.make_aware(datetime(2023, 1, 1, 10, 0, 0)),
            current_status="firing",
            total_firing_count=1
        )
        self.alert_instance = AlertInstance.objects.create(
            alert_group=self.alert_group,
            status="firing",
            started_at=timezone.make_aware(datetime(2023, 1, 1, 10, 0, 0)),
            ended_at=None,
            annotations={"summary": "Test alert"},
            generator_url="http://example.com/generator"
        )

    def test_alert_instance_serialization(self):
        serializer = AlertInstanceSerializer(instance=self.alert_instance)
        data = serializer.data

        self.assertEqual(data['id'], self.alert_instance.id)
        self.assertEqual(data['status'], 'firing')
        self.assertEqual(data['started_at'], self.alert_instance.started_at.isoformat().replace('+00:00', 'Z'))
        self.assertIsNone(data['ended_at'])
        self.assertEqual(data['annotations'], {"summary": "Test alert"})
        self.assertEqual(data['generator_url'], "http://example.com/generator")
        self.assertEqual(data['alert_group_fingerprint'], self.alert_group.fingerprint)

    def test_get_alert_group_fingerprint_with_group(self):
        serializer = AlertInstanceSerializer(instance=self.alert_instance)
        self.assertEqual(serializer.data['alert_group_fingerprint'], self.alert_group.fingerprint)

    def test_get_alert_group_fingerprint_without_group(self):
        # Mock an AlertInstance where alert_group is None
        mock_alert_instance = MagicMock(spec=AlertInstance)
        mock_alert_instance.alert_group = None
        
        serializer = AlertInstanceSerializer(instance=mock_alert_instance)
        self.assertIsNone(serializer.data['alert_group_fingerprint'])