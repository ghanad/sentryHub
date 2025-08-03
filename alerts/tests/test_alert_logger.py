import json
import os
from tempfile import TemporaryDirectory

from django.test import TestCase, override_settings

from alerts.services.alert_logger import save_alert_to_file


class AlertLoggerTests(TestCase):
    def test_save_alert_to_file_creates_json_file(self):
        alert_data = {"message": "سلام", "level": "info"}
        with TemporaryDirectory() as temp_dir:
            with override_settings(BASE_DIR=temp_dir):
                save_alert_to_file(alert_data)
                logs_dir = os.path.join(temp_dir, "Logs")
                self.assertTrue(os.path.isdir(logs_dir))
                files = os.listdir(logs_dir)
                self.assertEqual(len(files), 1)
                filename = files[0]
                self.assertTrue(filename.startswith("alert_"))
                self.assertTrue(filename.endswith(".json"))
                file_path = os.path.join(logs_dir, filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = json.load(f)
                self.assertEqual(content, alert_data)
