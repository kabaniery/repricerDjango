from django.apps import AppConfig


class RepricerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'repricer'

    def ready(self):
        import psutil
        import os

        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if 'chrome' in proc.info['name'].lower():
                    pid = proc.info['pid']
                    os.kill(pid, 9)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
