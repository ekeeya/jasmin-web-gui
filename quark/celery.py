import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quark.settings')

app = Celery('quark')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps + explicit cron imports.
app.autodiscover_tasks()
app.conf.imports = tuple(
    dict.fromkeys(
        tuple(getattr(app.conf, "imports", ()) or ())
        + ("quark.crons.jasmin_user_sync", "quark.messaging.tasks")
    )
)
