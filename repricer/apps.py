import atexit
import logging

from django.apps import AppConfig
from django.db import connection


class RepricerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'repricer'
    manager = None

    def ready(self):
        from ChromeController.ProcessManager import Manager
        atexit.register(Manager.shutdown)

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'repricer' AND table_name = 'repricer_client';")
            if cursor.fetchone()[0] == 1:
                # ≈сли таблица существует, выполн€ем обновление
                from .models import Client, Product
                try:
                    Client.objects.update(product_blocked=False)
                    Product.objects.update(is_updating=False)
                except Exception:
                    logging.getLogger("django").warning("Can't update")



