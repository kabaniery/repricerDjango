from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Устанавливаем переменную окружения для настройки Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'repricerDjango.settings')
# Создаем экземпляр приложения Celery
app = Celery('repricerDjango')
# Загружаем настройки из файла Django
app.config_from_object('django.conf:settings', namespace='CELERY')
# Автоматически обнаруживаем задачи в приложениях Django
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
