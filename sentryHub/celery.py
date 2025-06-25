from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sentryHub.settings')

app = Celery('sentryHub')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
# The lambda function is not necessary with modern Celery/Django.
# The simple version is more robust.
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True) # Added ignore_result=True as it's a debug task
def debug_task(self):
    print(f'Request: {self.request!r}')

# Note: The logging configuration part can be removed if you handle logging
# in settings.py, which is generally cleaner. But leaving it here is also fine.
app.conf.worker_hijack_root_logger = False
app.conf.worker_log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
app.conf.worker_task_log_format = '%(asctime)s - %(name)s - %(levelname)s - %(task_name)s - %(message)s'