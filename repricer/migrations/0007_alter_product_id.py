# Generated by Django 5.1 on 2024-09-07 09:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('repricer', '0006_alter_product_unique_together_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='id',
            field=models.CharField(max_length=100, primary_key=True, serialize=False),
        ),
    ]