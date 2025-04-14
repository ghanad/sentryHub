from django.apps import AppConfig


class AlertsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'alerts'
    verbose_name = 'Alert Management'

    def ready(self):
        # Import and register signal handlers
        from . import handlers  # noqa