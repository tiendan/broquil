# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('elbroquil', '0003_producer_description'),
    ]

    operations = [
        migrations.AlterField(
            model_name='accountmovement',
            name='explanation',
            field=models.TextField(verbose_name='explanation', blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='distributionaccountdetail',
            name='notes',
            field=models.TextField(verbose_name='notes', blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='emaillist',
            name='description',
            field=models.TextField(verbose_name='description', blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='emaillist',
            name='email_addresses',
            field=models.TextField(verbose_name='email addresses', blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='emailtemplate',
            name='body',
            field=models.TextField(verbose_name='body', help_text='<em>(Do not remove the [[CONTENT]] parts.)</em>', blank=True, default=''),
        ),
#        migrations.AlterField(
#            model_name='emailtemplate',
#            name='email_code',
#            field=models.SmallIntegerField(verbose_name='email code', choices=[(1, 'Member: Offer Created'), (2, 'Member: Saturday Reminder'), (3, 'Member: Order Sent to Producers'), (4, 'Member: Account Created'), (5, 'Member: Distribution Task Reminder'), (101, 'Producer: Total Order'), (102, 'Producer: No Order This Week'), (103, 'Producer: Product Ratings')], default='ca'),
#        ),
#        migrations.AlterField(
#            model_name='emailtemplate',
#            name='language',
#            field=models.CharField(verbose_name='language code', max_length=2, choices=[('tr', 'Turkish'), ('ca', 'Catala'), ('es', 'Castellano'), ('en', 'English')], default='ca'),
#        ),
        migrations.AlterField(
            model_name='emailtemplate',
            name='subject',
            field=models.CharField(verbose_name='subject', max_length=70, blank=True, default='', help_text='<em>(Without [BroquilGotic])</em>'),
        ),
        migrations.AlterField(
            model_name='extrainfo',
            name='secondary_email',
            field=models.EmailField(verbose_name='secondary email', max_length=254, blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='extrainfo',
            name='secondary_phone',
            field=models.CharField(verbose_name='secondary phone', max_length=15, blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='producer',
            name='description',
            field=models.TextField(verbose_name='description', help_text='<em>(Long explanation about the producer. If you want to place photos or links to files, a) place them in Google Drive and create public link, b) find their public link from some other website)</em>', blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='producer',
            name='excel_format',
            field=models.SmallIntegerField(verbose_name='excel format', choices=[(0, 'Standard'), (1, 'Cal Rosset'), (2, 'Can Pipirimosca'), (3, 'La Selvatana'), (4, 'Can Perol')], default=0),
        ),
        migrations.AlterField(
            model_name='producer',
            name='short_product_explanation',
            field=models.CharField(verbose_name='short product explanation', max_length=80, default='', help_text="<em>(Will be shown on the 'offer created' emails.)</em>"),
        ),
    ]
