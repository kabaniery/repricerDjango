from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


# Create your models here.
class Client(AbstractUser):
    shop_name = models.CharField(max_length=100)
    shop_avatar = models.ImageField(upload_to='avatars/')
    product_blocked = models.BooleanField(default=False)
    api_key = models.CharField(max_length=50)
    last_update = models.DateTimeField(default=timezone.now)
    last_product = models.CharField(default="-1", null=True, max_length=20)


class Product(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    shop = models.ForeignKey(Client, on_delete=models.NOT_PROVIDED)
    offer_id = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    price = models.IntegerField()
    it = models.IntegerField(default=0)
    needed_price = models.IntegerField(null=True)
    to_removal = models.BooleanField(default=False)

    def __str__(self):
        return str(self.id)
