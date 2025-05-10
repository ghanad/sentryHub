"""
Django settings for sentryHub project.
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Watcher choices for Jira rules
WATCHER_CHOICES = [
    ('user1', 'User 1'),
    ('user2', 'User 2'),
    ('user3', 'User 3'),
    ('group1', 'Group 1'),
    ('group2', 'Group 2'),
]

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-replace-this-in-production-environment'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    'tinymce',
    
    # Project apps
    'core.apps.CoreConfig',
    'alerts',
    'docs',
    'users',
    'integrations',
    'dashboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.AdminAccessMiddleware',
]

ROOT_URLCONF = 'sentryHub.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'users/templates'), 
            os.path.join(BASE_DIR, 'templates'),
            os.path.join(BASE_DIR, 'main_dashboard/templates')
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.notifications',
            ],
        },
    },
]

WSGI_APPLICATION = 'sentryHub.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# For production, consider using PostgreSQL:
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'sentryhub',
#         'USER': 'sentryhub_user',
#         'PASSWORD': 'password',
#         'HOST': 'localhost',
#         'PORT': '5432',
#     }
# }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO', # Capture DEBUG level logs in the file
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs/sentryhub.log', # Ensure this path is correct
            'maxBytes': 1024*1024*5, # 5 MB
            'backupCount': 2,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO', # Only show INFO and above in console
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO', # Keep Django DEBUG for file log clarity
            'propagate': False,
        },
        'alerts': { # Logger for the 'alerts' app including 'alerts.tasks'
            'handlers': ['console', 'file'],
            'level': 'INFO', # Keep DEBUG to capture all logs in file
            'propagate': False,
        },
        # You might need a specific logger for celery if the above doesn't work
        # 'celery': {
        #     'handlers': ['console', 'file'],
        #     'level': 'INFO',
        #     'propagate': True,
        # },
        # Root logger catches everything else
        '': {
            'handlers': ['console', 'file'],
            'level': 'INFO', # Root level INFO for console
            'propagate': False,
        },
    },
}

# Rest Framework Settings
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
}

# Login/Logout URLs
LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = 'dashboard:dashboard'
LOGOUT_REDIRECT_URL = '/users/login/'

# API Webhook settings - for production, this should require authentication
WEBHOOK_REQUIRE_AUTH = False

# TinyMCE Configuration
TINYMCE_DEFAULT_CONFIG = {
    'height': 360,
    'width': '100%',
    'cleanup_on_startup': True,
    'custom_undo_redo_levels': 20,
    'selector': 'textarea',
    'theme': 'silver',
    'plugins': '''
        textcolor save link image media preview table contextmenu
        fileupload table code lists fullscreen insertdatetime nonbreaking
        contextmenu directionality searchreplace wordcount visualblocks
        visualchars code fullscreen autolink lists charmap print hr
        anchor pagebreak
        ''',
    'toolbar1': '''
        fullscreen preview bold italic underline | fontselect,
        fontsizeselect | forecolor backcolor | alignleft alignright |
        aligncenter alignjustify | indent outdent | bullist numlist table |
        | link image media | forecolor backcolor emoticons | |
        ltr rtl | removeformat | help
        ''',
    'contextmenu': 'formats | link image',
    'menubar': True,
    'statusbar': True,
}

# Celery Configuration
CELERY_BROKER_URL = 'redis://172.20.82.3:6379/0'
CELERY_RESULT_BACKEND = 'redis://172.20.82.3:6379/0'
CELERY_ACCEPT_CONTENT = ['json'] # Reverted back to json
CELERY_TASK_SERIALIZER = 'json' # Reverted back to json
CELERY_RESULT_SERIALIZER = 'json' # Reverted back to json
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_DEFAULT_QUEUE = 'alerts'
CELERY_TASK_ROUTES = {
    'alerts.tasks.process_alert_payload_task': {'queue': 'alerts'},
}
# Removed redundant serializer settings
CELERY_TIMEZONE = TIME_ZONE

# RabbitMQ Configuration for External Alerts
RABBITMQ_CONFIG = {
    'HOST': os.environ.get('RABBITMQ_HOST', 'localhost'),
    'PORT': int(os.environ.get('RABBITMQ_PORT', 5672)),
    'EXTERNAL_QUEUE': os.environ.get('RABBITMQ_EXTERNAL_QUEUE', 'sentryhub_alerts_external'),
    'USER': os.environ.get('RABBITMQ_USER', 'guest'),
    'PASSWORD': os.environ.get('RABBITMQ_PASSWORD', 'guest'),
    'HEARTBEAT': int(os.environ.get('RABBITMQ_HEARTBEAT', 600)),
    'BLOCKED_CONNECTION_TIMEOUT': int(os.environ.get('RABBITMQ_BLOCKED_CONNECTION_TIMEOUT', 300)),
    'RETRY_DELAY': int(os.environ.get('RABBITMQ_RETRY_DELAY', 30)), # Seconds
}

SITE_URL = "https://sentryhub.tsetmc.com"
JIRA_CONFIG = {
    'server_url': 'https://jira.tsetmc.com',
    'username': 'monitoring',
    'password': 'tsemntmc@1404!',
    'allowed_project_keys': ['SAM'],
    'open_status_categories': ['To Do', 'In Progress'],
    'closed_status_categories': ['Done'],

    'ISSUE_TYPE_CHOICES': [
        ('Incident', 'Incident'),
        # ('task', 'Task'),
    ],
    # test issue
    'test_project_key': 'SAM',
    'test_issue_type': 'Incident',
}