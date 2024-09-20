import atexit
import os

from django.apps import AppConfig
from ChromeController.ProcessManager import Manager
from multiprocessing import Manager as M


class RepricerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'repricer'
    manager = None

    def ready(self):
        print("Django started")
        RepricerConfig.manager = Manager(-1, None)


atexit.register(Manager.shutdown())
