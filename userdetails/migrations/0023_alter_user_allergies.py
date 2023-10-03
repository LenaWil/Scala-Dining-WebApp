# Generated by Django 4.1.4 on 2023-10-03 18:14

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("userdetails", "0022_move_allergies"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="allergies",
            field=models.CharField(
                blank=True,
                help_text="E.g. gluten or vegetarian. Leave empty if not applicable.",
                max_length=1000,
                verbose_name="food allergies or preferences",
            ),
        ),
    ]
