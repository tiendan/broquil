# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('elbroquil', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AccountMovement',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('movement_type', models.SmallIntegerField(default=1, verbose_name='movement type', choices=[(1, 'Transfer from SAFE to DRAWER'), (2, 'Transfer from DRAWER to SAFE')])),
                ('amount', models.DecimalField(default=0, verbose_name='amount', max_digits=7, decimal_places=2)),
                ('final_amount', models.DecimalField(default=0, verbose_name='final amount in safe', max_digits=7, decimal_places=2)),
                ('explanation', models.TextField(default=b'', verbose_name='explanation', blank=True)),
                ('movement_date', models.DateTimeField(default=django.utils.timezone.now, verbose_name='movement date')),
            ],
        ),
    ]
