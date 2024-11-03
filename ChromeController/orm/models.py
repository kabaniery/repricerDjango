from tortoise import fields
from tortoise.models import Model
from datetime import datetime, timezone


def get_now():
    return datetime.now(timezone.utc)


class Client(Model):
    id = fields.BigIntField(pk=True)
    password = fields.CharField(max_length=128)
    last_login = fields.DatetimeField(null=True)
    is_superuser = fields.BooleanField()
    username = fields.CharField(max_length=150, unique=True)
    first_name = fields.CharField(max_length=150)
    last_name = fields.CharField(max_length=150)
    email = fields.CharField(max_length=254)
    is_staff = fields.BooleanField()
    is_active = fields.BooleanField()
    date_joined = fields.DatetimeField()
    shop_name = fields.CharField(max_length=100)
    shop_avatar = fields.CharField(max_length=100)
    product_blocked = fields.BooleanField()
    api_key = fields.CharField(max_length=50)
    last_product = fields.CharField(max_length=20, null=True)

    class Meta:
        table = "repricer_client"


class Product(Model):
    id = fields.CharField(max_length=100, pk=True)

    shop = fields.ForeignKeyField("models.Client", related_name="products", on_delete=fields.CASCADE)  # Связь с Client

    offer_id = fields.CharField(max_length=20)
    name = fields.CharField(max_length=100, null=True)
    sku = fields.CharField(max_length=50, null=True)

    price = fields.IntField()
    needed_price = fields.IntField(null=True)

    to_removal = fields.BooleanField(default=False)
    is_updating = fields.BooleanField(default=False)
    last_update = fields.DatetimeField(default=get_now)

    class Meta:
        table = "repricer_product"
