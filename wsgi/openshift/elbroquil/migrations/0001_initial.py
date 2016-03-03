# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone
from django.conf import settings
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='name')),
                ('visible_name', models.CharField(help_text='<em>(To display shorter/better names for producer categories.)</em>', max_length=100, null=True, verbose_name='visible name', blank=True)),
                ('sort_order', models.PositiveIntegerField(default=0, help_text='<em>(To change the order of appearance of categories.)</em>', verbose_name='sort order')),
                ('archived', models.BooleanField(default=False, verbose_name='archived')),
            ],
            options={
                'verbose_name': 'category',
                'verbose_name_plural': 'categories',
            },
        ),
        migrations.CreateModel(
            name='Consumption',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('amount', models.DecimalField(default=0, verbose_name='quantity', max_digits=7, decimal_places=2)),
            ],
        ),
        migrations.CreateModel(
            name='Debt',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('amount', models.DecimalField(default=0, verbose_name='quantity', max_digits=7, decimal_places=2)),
            ],
        ),
        migrations.CreateModel(
            name='DistributionAccountDetail',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateField(default=django.utils.timezone.now, verbose_name='distribution date')),
                ('initial_amount', models.DecimalField(default=0, verbose_name='initial amount', max_digits=7, decimal_places=2)),
                ('member_consumed_amount', models.DecimalField(default=0, verbose_name='member consumed amount', max_digits=7, decimal_places=2)),
                ('total_member_payment_amount', models.DecimalField(default=0, verbose_name='total member payment amount', max_digits=7, decimal_places=2)),
                ('debt_balance_amount', models.DecimalField(default=0, verbose_name='debt balance amount', max_digits=7, decimal_places=2)),
                ('quarterly_fee_collected_amount', models.DecimalField(default=0, verbose_name='collected fee amount', max_digits=7, decimal_places=2)),
                ('final_amount', models.DecimalField(default=0, verbose_name='final amount', max_digits=7, decimal_places=2)),
                ('expected_final_amount', models.DecimalField(default=0, verbose_name='expected final amount', max_digits=7, decimal_places=2)),
                ('notes', models.TextField(default=b'', verbose_name='notes', blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='DistributionTask',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('distribution_date', models.DateField(verbose_name='distribution date')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='EmailList',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=80, verbose_name='name')),
                ('description', models.TextField(default=b'', verbose_name='description', blank=True)),
                ('email_addresses', models.TextField(default=b'', verbose_name='email addresses', blank=True)),
                ('cc_task_reminders', models.BooleanField(default=False, verbose_name='cc task reminders')),
                ('cc_incidents', models.BooleanField(default=False, verbose_name='cc incidents')),
            ],
        ),
        migrations.CreateModel(
            name='EmailTemplate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('email_code', models.SmallIntegerField(default=b'ca', verbose_name='email code', choices=[(1, 'Member: Offer Created'), (2, 'Member: Saturday Reminder'), (3, 'Member: Order Sent to Producers'), (4, 'Member: Account Created'), (5, 'Member: Distribution Task Reminder'), (101, 'Producer: Total Order'), (102, 'Producer: No Order This Week'), (103, 'Producer: Product Ratings')])),
                ('language', models.CharField(default=b'ca', max_length=2, verbose_name='language code', choices=[(b'tr', 'Turkish'), (b'ca', 'Catala'), (b'es', 'Castellano'), (b'en', 'English')])),
                ('subject', models.CharField(default=b'', help_text='<em>(Without [BroquilGotic])</em>', max_length=70, verbose_name='subject', blank=True)),
                ('body', models.TextField(default=b'', help_text='<em>(Do not remove the [[CONTENT]] parts.)</em>', verbose_name='body', blank=True)),
            ],
            options={
                'verbose_name': 'email template',
                'verbose_name_plural': 'email templates',
            },
        ),
        migrations.CreateModel(
            name='ExtraInfo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('secondary_email', models.EmailField(default=b'', max_length=254, verbose_name='secondary email', blank=True)),
                ('phone', models.CharField(max_length=15, verbose_name='phone')),
                ('secondary_phone', models.CharField(default=b'', max_length=15, verbose_name='secondary phone', blank=True)),
                ('user', models.OneToOneField(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('quantity', models.DecimalField(verbose_name='quantity', max_digits=7, decimal_places=2)),
                ('rating', models.SmallIntegerField(default=None, null=True, verbose_name='rating', blank=True)),
                ('archived', models.BooleanField(default=False, verbose_name='archived')),
                ('status', models.SmallIntegerField(default=0, verbose_name='status', choices=[(0, 'Normal'), (10, 'Did not arrive'), (20, 'Min. order not met')])),
                ('arrived_quantity', models.DecimalField(verbose_name='arrived quantity', max_digits=7, decimal_places=2)),
            ],
            options={
                'verbose_name': 'order',
                'verbose_name_plural': 'orders',
            },
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date')),
                ('amount', models.DecimalField(default=0, verbose_name='quantity', max_digits=7, decimal_places=2)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Producer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('first_name', models.CharField(max_length=50, verbose_name='first name')),
                ('last_name', models.CharField(max_length=50, null=True, verbose_name='last name', blank=True)),
                ('company_name', models.CharField(max_length=50, null=True, verbose_name='company name', blank=True)),
                ('email', models.EmailField(max_length=254, verbose_name='email')),
                ('send_ratings', models.BooleanField(default=False, verbose_name='send ratings')),
                ('order_day', models.SmallIntegerField(default=0, verbose_name='order day', choices=[(0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')])),
                ('order_hour', models.SmallIntegerField(verbose_name='order hour', validators=[django.core.validators.MaxValueValidator(23), django.core.validators.MinValueValidator(0)])),
                ('minimum_order', models.DecimalField(null=True, verbose_name='minimum order', max_digits=7, decimal_places=2, blank=True)),
                ('fixed_products', models.BooleanField(default=False, verbose_name='fixed products')),
                ('limited_availability', models.BooleanField(default=False, verbose_name='limited availability')),
                ('excel_format', models.SmallIntegerField(default=0, verbose_name='excel format', choices=[(0, 'Standard'), (1, b'Cal Rosset'), (2, b'Can Pipirimosca'), (3, b'La Selvatana'), (4, b'Can Perol')])),
                ('default_category_name', models.CharField(max_length=50, null=True, verbose_name='default category name', blank=True)),
                ('active', models.BooleanField(default=True, help_text='<em>(Disable the producer by clearing this option.)</em>', verbose_name='active')),
                ('transportation_cost', models.DecimalField(default=0, verbose_name='transportation cost', max_digits=7, decimal_places=2)),
                ('short_product_explanation', models.CharField(default=b'', help_text="<em>(Will be shown on the 'offer created' emails.)</em>", max_length=80, verbose_name='short product explanation')),
            ],
            options={
                'verbose_name': 'producer',
                'verbose_name_plural': 'producers',
            },
        ),
        migrations.CreateModel(
            name='ProducerAvailableDate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('available_date', models.DateField(verbose_name='available date')),
                ('producer', models.ForeignKey(to='elbroquil.Producer')),
            ],
            options={
                'verbose_name': 'available date',
                'verbose_name_plural': 'available dates',
            },
        ),
        migrations.CreateModel(
            name='ProducerPayment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateField(default=django.utils.timezone.now, verbose_name='distribution date')),
                ('amount', models.DecimalField(default=0, verbose_name='quantity', max_digits=7, decimal_places=2)),
                ('producer', models.ForeignKey(to='elbroquil.Producer')),
            ],
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='product')),
                ('origin', models.CharField(max_length=100, null=True, verbose_name='origin', blank=True)),
                ('comments', models.CharField(max_length=100, null=True, verbose_name='comments', blank=True)),
                ('price', models.DecimalField(verbose_name='price', max_digits=9, decimal_places=4)),
                ('unit', models.CharField(help_text='<em>(without the &euro; sign or / character.)</em>', max_length=20, verbose_name='unit')),
                ('integer_demand', models.BooleanField(default=False, verbose_name='integer demand')),
                ('distribution_date', models.DateField(help_text='<em>(Only fill for products that are offered just once.)</em>', null=True, verbose_name='distribution date', blank=True)),
                ('archived', models.BooleanField(default=False, verbose_name='archived')),
                ('total_quantity', models.DecimalField(default=0, verbose_name='total quantity', max_digits=7, decimal_places=2)),
                ('arrived_quantity', models.DecimalField(default=0, verbose_name='arrived quantity', max_digits=7, decimal_places=2)),
                ('order_limit_date', models.DateTimeField(help_text='<em>(Only fill for products that are offered just once.)</em>', null=True, verbose_name='order limit date', blank=True)),
                ('average_rating', models.DecimalField(default=0, verbose_name='average rating', max_digits=5, decimal_places=1)),
                ('new_product', models.BooleanField(default=False, help_text='<em>(To highlight this product as NEW in the order pages.)</em>', verbose_name='new product')),
                ('sent_to_producer', models.BooleanField(default=False, verbose_name='sent to producer')),
                ('stock_product', models.BooleanField(default=False, verbose_name='stock product')),
                ('category', models.ForeignKey(to='elbroquil.Category')),
            ],
            options={
                'verbose_name': 'product',
                'verbose_name_plural': 'products',
            },
        ),
        migrations.CreateModel(
            name='Quarterly',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('year', models.SmallIntegerField(verbose_name='year')),
                ('quarter', models.SmallIntegerField(verbose_name='quarter')),
                ('created_date', models.DateTimeField(default=django.utils.timezone.now, verbose_name='created date')),
                ('amount', models.DecimalField(default=0, verbose_name='quantity', max_digits=7, decimal_places=2)),
                ('payment', models.ForeignKey(to='elbroquil.Payment', null=True)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='SkippedDistributionDate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('skipped_date', models.DateField(verbose_name='skipped date')),
            ],
            options={
                'verbose_name': 'skipped date',
                'verbose_name_plural': 'skipped dates',
            },
        ),
        migrations.AddField(
            model_name='order',
            name='product',
            field=models.ForeignKey(to='elbroquil.Product'),
        ),
        migrations.AddField(
            model_name='order',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='debt',
            name='payment',
            field=models.ForeignKey(to='elbroquil.Payment'),
        ),
        migrations.AddField(
            model_name='debt',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='consumption',
            name='payment',
            field=models.ForeignKey(to='elbroquil.Payment'),
        ),
        migrations.AddField(
            model_name='consumption',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='category',
            name='producer',
            field=models.ForeignKey(to='elbroquil.Producer'),
        ),
    ]
