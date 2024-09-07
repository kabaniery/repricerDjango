from django.db import models
from django.contrib.auth.models import AbstractUser


# Create your models here.
class Client(AbstractUser):

    shop_name = models.CharField(max_length=50)
    shop_address = models.CharField(max_length=50)
    shop_avatar = models.ImageField(upload_to='avatars/')
    product_blocked = models.BooleanField(default=False)
    api_key = models.CharField(max_length=50)


class Product(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    shop = models.ForeignKey(Client, on_delete=models.NOT_PROVIDED)
    offer_id = models.CharField(max_length=20)
    name = models.CharField(max_length=50)
    price = models.IntegerField()
    gray_price = models.IntegerField(default=-1)
    it = models.IntegerField(default=0)

    def __str__(self):
        return str(self.id)

