# Generated by Django 5.1 on 2024-10-03 13:08

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('repricer', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='gray_price',
        ),
        migrations.AddField(
            model_name='client',
            name='last_update',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='product',
            name='needed_price',
            field=models.IntegerField(null=True),
        ),
    ]
