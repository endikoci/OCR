# celery.py

from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'OCR.settings')

app = Celery("OCR")
app.conf.broker_url = 'redis://127.0.0.1:6379/0'

app.conf.enable_utc = False
app.conf.update(timezone='Europe/Tirane')
app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()


app.conf.beat_schedule = {
    'add-every-5-seconds': {
        'task': 'process_uploaded_file',
        'schedule': 5.0,
        'args': ('user_email', 'uploaded_file'),
    },
    'add-every-minute-contrab': {
        'task': 'send_email_with_attachment',
        'schedule': crontab(minute=1),
        'args': ('receiver_email', 'subject', 'body', 'attachment_path'),
    },
}