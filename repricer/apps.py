import atexit
import logging

import redis
from django.apps import AppConfig
from django.db import connection
from redis import Redis


class RepricerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'repricer'
    broker: Redis = None

    def shutdown(self):
        if self.broker is not None:
            self.broker.lpush("important", "destroy")

    def ready(self):
        self.broker = redis.StrictRedis(host='localhost', port=6379, db=0)

        atexit.register(self.shutdown)

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



