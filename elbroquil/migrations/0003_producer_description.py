# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('elbroquil', '0002_accountmovement'),
    ]

    operations = [
        migrations.AddField(
            model_name='producer',
            name='description',
            field=models.TextField(default=b'', help_text='<em>(Long explanation about the producer. If you want to place photos or links to files, a) place them in Google Drive and create public link, b) find their public link from some other website)</em>', verbose_name='description', blank=True),
        ),
    ]
