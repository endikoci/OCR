# celery.py

from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from django.conf import settings


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'OCR.settings')

app = Celery("OCR")
app.conf.broker_url = 'redis://127.0.0.1:6379/0'

app.conf.enable_utc = False
app.conf.update(timezone='Europe/Tirane')
app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()


