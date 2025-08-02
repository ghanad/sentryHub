import collections
import threading
import os
import tempfile
import logging
import time
from django.conf import settings

logger = logging.getLogger(__name__)

class MetricManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(MetricManager, cls).__new__(cls)
                    cls._instance._initialized = False # Use a flag to prevent re-initialization
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.counters = collections.defaultdict(lambda: collections.defaultdict(int))
        self.gauges = collections.defaultdict(lambda: collections.defaultdict(float))
        self._lock = threading.Lock() # Re-initialize lock for the instance
        self._initialized = True

    def inc_counter(self, name, labels=None, value=1):
        if not settings.METRICS_ENABLED:
            return
        with self._lock:
            label_key = self._format_labels(labels)
            self.counters[name][label_key] += value
            logger.debug(f"Incremented counter {name}{{{label_key}}} by {value}")

    def set_gauge(self, name, labels=None, value=0.0):
        if not settings.METRICS_ENABLED:
            return
        with self._lock:
            label_key = self._format_labels(labels)
            self.gauges[name][label_key] = value
            logger.debug(f"Set gauge {name}{{{label_key}}} to {value}")

    def _format_labels(self, labels):
        if not labels:
            return ""
        # Sort labels by key for consistent output
        sorted_labels = sorted(labels.items())
        return ",".join([f'{key}="{value}"' for key, value in sorted_labels])

    def write_metrics(self):
        if not settings.METRICS_ENABLED:
            return

        logger.info("Writing metrics to file")
        temp_file = None
        try:
            # Use mkstemp for atomic file creation
            fd, temp_path = tempfile.mkstemp(suffix=".prom", dir=os.path.dirname(settings.METRICS_FILE_PATH))
            
            # Capture current timestamp as a Unix timestamp
            current_time = time.time()

            with os.fdopen(fd, 'w') as f:
                # Write counters
                for name, labels_dict in self.counters.items():
                    f.write(f'# TYPE {name} counter\n')
                    for label_key, value in labels_dict.items():
                        if label_key:
                            f.write(f'{name}{{{label_key}}} {value}\n')
                        else:
                            f.write(f'{name} {value}\n')

                # Write gauges
                for name, labels_dict in self.gauges.items():
                    f.write(f'# TYPE {name} gauge\n')
                    for label_key, value in labels_dict.items():
                        if label_key:
                            f.write(f'{name}{{{label_key}}} {value}\n')
                        else:
                            f.write(f'{name} {value}\n')

                # Manually write the timestamp metric directly to the file
                f.write(f'# TYPE sentryhub_last_metrics_write_timestamp gauge\n')
                f.write(f'sentryhub_last_metrics_write_timestamp {current_time}\n')

            # Atomically replace the target file
            os.rename(temp_path, settings.METRICS_FILE_PATH)
            logger.info(f"Successfully wrote metrics to {settings.METRICS_FILE_PATH}")

        except Exception as e:
            logger.error(f"Error writing metrics to file: {e}")
            # Clean up temporary file if it was created but rename failed
            if temp_file and os.path.exists(temp_file):
                os.remove(temp_file)

# Global instance
metrics_manager = MetricManager()