# Generated by Django 2.1.5 on 2019-02-09 16:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('UserDetails', '0006_auto_20190207_1744'),
    ]

    operations = [
        migrations.AddField(
            model_name='association',
            name='is_choosable',
            field=models.BooleanField(default=True, verbose_name='Whether this association can be chosen as membership by users'),
        ),
    ]
