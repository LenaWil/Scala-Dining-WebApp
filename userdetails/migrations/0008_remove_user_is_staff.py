# Generated by Django 2.1.3 on 2019-02-27 15:49

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("userdetails", "0007_association_is_choosable"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="is_staff",
        ),
    ]
