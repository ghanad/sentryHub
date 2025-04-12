# docs/apps.py

from django.apps import AppConfig

class DocsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'docs'
    verbose_name = 'Alert Documentation'
    
    def ready(self):
        import docs.signals