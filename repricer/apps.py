import atexit

import redis
from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.dispatch import receiver
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
        post_migrate.connect(set_product_blocked_false, sender=self)


@receiver(post_migrate)
def set_product_blocked_false(sender, **kwargs):
    from repricer.models import Client
    Client.objects.update(product_blocked=False)
