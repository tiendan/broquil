# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('elbroquil', '0006_distributionaccountdetail_expected_initial_amount'),
    ]

    operations = [
        migrations.CreateModel(
            name='DistributionDate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('distribution_date', models.DateField(verbose_name='distribution date')),
                ('canceled', models.BooleanField(verbose_name='canceled')),
            ],
            options={
                'verbose_name': 'distribution date',
                'verbose_name_plural': 'distribution dates',
            },
        ),
        migrations.DeleteModel(
            name='SkippedDistributionDate',
        ),
    ]
