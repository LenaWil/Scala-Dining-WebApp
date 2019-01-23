# Generated by Django 2.1.5 on 2019-01-22 13:07

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from General.DBView_migration import CreateView


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('UserDetails', '0001_initial'),
        ('CreditManagement', '0001_initial'),
    ]

    operations = [
        CreateView(
            name='UserCredit',
            fields=[
                ('user', models.OneToOneField(db_column='id', on_delete=django.db.models.deletion.DO_NOTHING, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('balance', models.DecimalField(blank=True, db_column='balance', decimal_places=2, max_digits=6, null=True)),
            ],
        ),
    ]
