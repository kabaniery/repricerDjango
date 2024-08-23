# Generated by Django 5.1 on 2024-08-22 12:33

import django.db.models.fields
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('repricer', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='product_blocked',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='product',
            name='shop',
            field=models.ForeignKey(default=0, on_delete=django.db.models.fields.NOT_PROVIDED, to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
    ]
