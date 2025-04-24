# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('elbroquil', '0005_auto_20171121_0106'),
    ]

    operations = [
        migrations.AddField(
            model_name='distributionaccountdetail',
            name='expected_initial_amount',
            field=models.DecimalField(verbose_name='expected initial amount', default=0, max_digits=7, decimal_places=2),
        ),
    ]
