import atexit
import os

from django.apps import AppConfig


class RepricerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'repricer'
    manager = None

    def ready(self):
        print("Django started")


from ChromeController.ProcessManager import Manager
atexit.register(Manager.shutdown)
