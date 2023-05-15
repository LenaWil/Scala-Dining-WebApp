# Generated by Django 4.1.4 on 2023-03-10 01:05

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('userdetails', '0022_move_allergies'),
        ('creditmanagement', '0016_unfold_cancel_column'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='transaction',
            name='cancelled',
        ),
        migrations.RemoveField(
            model_name='transaction',
            name='cancelled_by',
        ),
        migrations.AlterField(
            model_name='account',
            name='association',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='userdetails.association'),
        ),
        migrations.AlterField(
            model_name='account',
            name='user',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='description',
            field=models.CharField(max_length=1000),
        ),
    ]
