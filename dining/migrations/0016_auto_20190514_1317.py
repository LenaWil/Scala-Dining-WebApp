# Generated by Django 2.2 on 2019-05-14 11:17

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("dining", "0015_auto_20190513_2104"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="dininglist",
            name="claimed_by",
        ),
        migrations.AlterField(
            model_name="dininglist",
            name="main_contact",
            field=models.ForeignKey(
                blank=True,
                help_text="If specified, is shown on the dining list as the main contact. The owners are always shown.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="main_contact_dining_lists",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="dininglist",
            name="owners",
            field=models.ManyToManyField(
                blank=True,
                help_text="Owners can manage the dining list.",
                related_name="owned_dining_lists",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="dininglist",
            name="purchaser",
            field=models.ForeignKey(
                blank=True,
                help_text="If specified, is shown on the dining list as the user who should receive the grocery shopping payments.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="purchaser_dining_lists",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
