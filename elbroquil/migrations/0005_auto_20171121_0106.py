# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('elbroquil', '0004_auto_20171120_2354'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailtemplate',
            name='email_code',
            field=models.SmallIntegerField(choices=[(1, 'Member: Offer Created'), (2, 'Member: Saturday Reminder'), (3, 'Member: Order Sent to Producers'), (4, 'Member: Account Created'), (5, 'Member: Distribution Task Reminder'), (101, 'Producer: Total Order'), (102, 'Producer: No Order This Week'), (103, 'Producer: Product Ratings')], default='ca', verbose_name='email code'),
        ),
        migrations.AlterField(
            model_name='emailtemplate',
            name='language',
            field=models.CharField(choices=[('tr', 'Turkish'), ('ca', 'Catala'), ('es', 'Castellano'), ('en', 'English')], verbose_name='language code', max_length=2, default='ca'),
        ),
    ]
