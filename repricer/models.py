from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


# Create your models here.
class Client(AbstractUser):
    api_key = models.CharField(max_length=50)

    shop_name = models.CharField(max_length=100, null=True)
    shop_avatar = models.ImageField(upload_to='avatars/', null=True)

    product_blocked = models.BooleanField(default=False)
    last_product = models.CharField(null=True, max_length=20)


class Product(models.Model):
    id = models.CharField(max_length=100, primary_key=True)

    shop = models.ForeignKey(Client, on_delete=models.NOT_PROVIDED)

    offer_id = models.CharField(max_length=20)
    name = models.CharField(max_length=100, null=True)

    price = models.IntegerField()
    needed_price = models.IntegerField(null=True)

    to_removal = models.BooleanField(default=False)
    is_updating = models.BooleanField(default=False)
    last_update = models.DateTimeField(default=timezone.now())

    def __str__(self):
        return str(self.id)
