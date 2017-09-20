"""
Django settings for app project.

Generated by 'django-admin startproject' using Django 1.8.2.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""
import os
import sys
from urllib.parse import urljoin

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Dir where APNS push certificates are stored.
CERT_DIR = os.path.join(BASE_DIR, 'deploy/local/')

DEBUG = os.environ.get('DEBUG', False)

SECRET_KEY = os.environ.get('SECRET_KEY', 'my-secret-key')

ALLOWED_HOSTS = ['*']

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'raven.contrib.django.raven_compat',
    'rest_framework',
    'app',
    'api',
    'django_nose',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
)

ROOT_URLCONF = 'main.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'main.wsgi.application'

# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = False
USE_L10N = False
USE_TZ = False

STATIC_ROOT = os.path.join(BASE_DIR, 'final_static')
STATIC_URL = '/static/'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        # 'rest_framework.authentication.TokenAuthentication',
        # 'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        # 'rest_framework.permissions.IsAuthenticated',
    ),
}

# Tags used for APNS environments.
APNS_PRODUCTION = 'push_production'
APNS_SANDBOX = 'push_sandbox'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': '/var/tmp/django_cache',
    },
}

# List of redis cluster nodes eq. '127.0.0.1:6789,123.4.5.6:7895'.
REDIS_SERVER_LIST = os.environ.get('REDIS_SERVER_LIST', 'redis:7000')

# URL send with push notification payload so the app can respond to the right
# server.
APP_API_URL = os.environ.get('APP_API_URL')
APP_PUSH_ROUNDTRIP_WAIT = int(os.environ.get('APP_PUSH_ROUNDTRIP_WAIT', 4000))
APP_PUSH_RESEND_INTERVAL = int(os.environ.get('APP_PUSH_RESEND_INTERVAL', 1000))

LOGGING_DIR = os.environ.get('LOGGING_DIR', '/var/log/middleware')
LOG_SOURCE = 'web-app'

MANAGERS = ADMINS = ('noc+middleware@voipgrid.nl',)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s {0} %(asctime)s %(message)s'.format(LOG_SOURCE)
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        }
    },
    'handlers': {
        'sentry': {
            'level': 'ERROR',
            'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
            'tags': {'custom-tag': 'x'},
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'formatter': 'verbose',
            'filename': os.path.join(LOGGING_DIR, 'middleware.log'),
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file', 'mail_admins'],
            'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'),
        },
    },
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DB_ENV_NAME', 'middleware'),
        'USER': os.environ.get('DB_ENV_USER', 'dev'),
        'PASSWORD': os.environ.get('DB_ENV_PASSWORD', 'dev1234'),
        'HOST': os.environ.get('DB_ENV_HOST', 'db'),
        'PORT': os.environ.get('DB_ENV_PORT', '4040'),
    }
}

# VG stands for VoIPGRID. This is the platform that handles all the sip
# traffic and is used for authenticating api requests in our implementation.
VG_API_BASE_URL = os.environ.get('VG_API_BASE_URL', 'http://172.17.0.5:8001')
VG_API_USER_URL = urljoin(VG_API_BASE_URL, os.environ.get('VG_API_USER_URL', '/api/permission/systemuser/profile/'))

# Testing
TESTING = os.environ.get('TESTING', sys.argv[1:2] == ['test'])
PERFORMANCE_TEST_ITERATIONS = os.environ.get('PERFORMANCE_TEST_ITERATIONS', 1)
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'


RAVEN_CONFIG = {
    'dsn': os.environ.get('SENTRY_DSN', None),
}

try:
    from .local_settings import *
except ImportError:
    pass
