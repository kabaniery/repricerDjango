from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# ������������� ���������� ��������� ��� ��������� Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'repricerDjango.settings')
# ������� ��������� ���������� Celery
app = Celery('repricerDjango')
# ��������� ��������� �� ����� Django
app.config_from_object('django.conf:settings', namespace='CELERY')
# ������������� ������������ ������ � ����������� Django
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
