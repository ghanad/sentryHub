from celery import shared_task
from .services.metrics import metrics_manager
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@shared_task
def flush_metrics_to_file():
    """
    Celery task to periodically flush in-memory metrics to the metrics file.
    """
    logger.info("Running flush_metrics_to_file task")
    if settings.METRICS_ENABLED:
        metrics_manager.write_metrics()
    else:
        logger.info("Metrics are disabled, skipping flush.")