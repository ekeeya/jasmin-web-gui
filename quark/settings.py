#
#  Copyright (c) 2024
#  File created on 2024/7/17
#  By: Emmanuel Keeya
#  Email: ekeeya@thothcode.tech
#
#  This project is licensed under the GNU General Public License v3.0. You may
#  redistribute it and/or modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This project is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
#  without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#  See the GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along with this project.
#  If not, see <http://www.gnu.org/licenses/>.
#

import os
from pathlib import Path
from .private_settings import *
from .datasource import *

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-nl7ec)b+qk$@ytxui!65^bt27x&538$g7h@i&l#282l-#&jpa$'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG", "True").lower() in ("1", "true", "yes", "y", "on")

ALLOWED_HOSTS = ["*"]

# Allow local dev origins behind nginx/localhost.
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    "django.forms",
    'rest_framework',
    'django_countries',
    'smartmin',
    'quark.web',
    'quark.jasmin',
    'quark.api',
    'quark.utils',
    'quark.workspace',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "quark.middleware.WorkspaceMiddleware",
    "quark.middleware.TimezoneMiddleware",
]

ROOT_URLCONF = 'quark.urls'

WSGI_APPLICATION = 'quark.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 6}},
]

# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True
USER_TIME_ZONE = "Africa/Kampala"

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

PROJECT_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)))

STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / "sitestatic"

MEDIA_ROOT = BASE_DIR / "media"

MEDIA_URL = "/media/"

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        "DIRS": [
            BASE_DIR / "templates",
        ],
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

FORM_RENDERER = 'django.forms.renderers.TemplatesSetting'

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = "workspace.User"

APP_LOG_FILE = os.path.join(BASE_DIR, 'logs', 'app.log')

os.makedirs(os.path.dirname(APP_LOG_FILE), exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {module} {process:d} {thread:d} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': APP_LOG_FILE,
            'formatter': 'verbose',
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
        },
    },
    'loggers': {
        '': {  # root logger
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'your_app_name': {  # Replace with your actual app name
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

JASMIN_PERSIST = True

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

SMARTMIN_DEFAULT_MESSAGES = True

# Smartmin settings
# https://smartmin.readthedocs.io/en/latest/perms.html#defining-permissions

PERMISSIONS = {
    '*': ('create',  # can create an object
          'read',  # can read an object, viewing it's details
          'update',  # can update an object
          'delete',  # can delete an object,
          'list',  # can view a list of the objects
          ),
    "workspace.workspace": (
        "signup",
        "read",
        "dashboard",
        "update",
        "delete",
        "list",),
    "jasmin.jasmingroup": ("activate", "deactivate"),
    "jasmin.jasminuser": ("activate", "deactivate"),
    "jasmin.jasminsmppconnector": ("start", "stop", "configure"),
    "jasmin.jasminhttpconnector": ("configure", ),
}

GROUP_PERMISSIONS = {
    "Administrators": (
        "workspace.workspace_create",
        "workspace.workspace_list",
        "workspace.workspace_dashboard",
        "workspace.workspace_update",
        "workspace.workspace_signup",
        "workspace.workspace_delete",
        "jasmin.jasmingroup_create",
        "jasmin.jasmingroup_update",
        "jasmin.jasmingroup_delete",
        "jasmin.jasmingroup_list",
        "jasmin.jasmingroup_activate",
        "jasmin.jasmingroup_deactivate",
        "jasmin.jasminuser_create",
        "jasmin.jasminuser_list",
        "jasmin.jasminuser_update",
        "jasmin.jasminuser_delete",
        "jasmin.jasminsmppconnector_configure",
        "jasmin.jasminsmppconnector_update",
        "jasmin.jasminsmppconnector_start",
        "jasmin.jasminsmppconnector_stop",
        "jasmin.jasminsmppconnector_delete",
        "jasmin.jasminsmppconnector_list",
        "jasmin.jasminhttpconnector_configure",
        "jasmin.jasminhttpconnector_update",
        "jasmin.jasminhttpconnector_delete",
        "jasmin.jasminhttpconnector_list",
        "jasmin.jasminfilter_create",
        "jasmin.jasminfilter_list",
        "jasmin.jasminfilter_delete",
        "jasmin.jasminroute_create",
        "jasmin.jasminroute_update",
        "jasmin.jasminroute_list",
        "jasmin.jasminroute_delete",
        "jasmin.jasmininterceptor_create",
        "jasmin.jasmininterceptor_update",
        "jasmin.jasmininterceptor_delete",
        "jasmin.jasmininterceptor_list",

    )
}

LOGIN_REDIRECT_URL = "/"
LOGIN_URL = "login/"
