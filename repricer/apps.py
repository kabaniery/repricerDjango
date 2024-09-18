import atexit

from django.apps import AppConfig
from ChromeController.ProcessManager import Manager


class RepricerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'repricer'
    manager = None

    def ready(self):
        print("Django started")
        self.manager = Manager(3)
        self.manager.start_project()
        print("Process manager started")





