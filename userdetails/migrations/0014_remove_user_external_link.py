# Generated by Django 2.2 on 2019-04-29 21:45

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("userdetails", "0013_auto_20190429_2232"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="external_link",
        ),
    ]
