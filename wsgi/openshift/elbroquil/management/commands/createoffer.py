# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from decimal import Decimal
import email
import imaplib
import os
import settings
import xlrd

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

import elbroquil.libraries as libs
import elbroquil.models as models
import elbroquil.parse as parser


class Command(BaseCommand):
    help = 'Crea la oferta y informa los miembros activos'

    def handle(self, *args, **options):
        # Check if there will be an offer this week (exclude today in case
        # it is Wednesday)
        next_dist_date = libs.get_next_distribution_date(False)

        days_until_next_distribution = (next_dist_date - libs.get_today()).days

        # If there is more than one week until next distribution date,
        # do not create offer
        if days_until_next_distribution > 7:
            self.stdout.write(
                """Quedan %d dias para la proxima fecha de distribucion """
                """(%s). NO se creara la oferta.""" %
                (days_until_next_distribution,
                    next_dist_date.strftime('%d/%m/%Y')))
            return

        # Get Cal Rosset producer record, read the excel
        # and parse the products
        cal_rosset = models.Producer.objects.filter(
            excel_format=models.CAL_ROSSET).first()

        # Fetch Cal Rosset excel file from Gmail and get the local file path
        self.stdout.write(
            'Intentando descargar el excel del productor principal...')

        excel_file_path = self.download_cal_rosset_excel()

        if excel_file_path == "":
            self.stderr.write(
                'Problema al descargar el excel del productor principal.')
            return

        self.stdout.write('El excel se ha descargado correctamente.')

        book = xlrd.open_workbook(excel_file_path)
        products = parser.parse_cal_rosset(book)

        # In a transaction
        with transaction.atomic():
            # Delete old products from the same producer
            models.Product.objects.filter(
                distribution_date=None,
                category__producer_id=cal_rosset.id).delete()

            # Insert new products one by one
            for product in products:
                category_text = product[0]
                name_text = product[1].strip()
                price_text = str(product[2]).replace(',', '.')
                unit_text = product[3]
                origin_text = product[4]
                comments_text = product[5]

                # Clean the unit text and remove currency char and extra chars
                unit_text = unit_text \
                    .replace(u'€', '') \
                    .replace('*', '') \
                    .replace('/', '').strip()

                # If comments include the word unitat, or the unit is not kilos
                # the demand should be made in units
                integer_demand = "unitat" in comments_text.lower() or \
                    unit_text.lower() != "kg"

                # For some exceptions, update the integer_demand value
                for exceptional_product in [
                        u"carabassa",
                        u"carbassa",
                        u"síndria",
                        u"meló"]:
                    integer_demand = integer_demand or \
                        exceptional_product in name_text.lower()

                category, _ = models.Category.objects.get_or_create(
                    name=category_text,
                    producer_id=cal_rosset.id)

                # Create and save the product
                prod = models.Product(
                    name=name_text,
                    category_id=category.id,
                    origin=origin_text,
                    comments=comments_text,
                    price=Decimal(price_text),
                    unit=unit_text,
                    integer_demand=integer_demand)
                prod.save()

            self.stdout.write(
                'Se han importado %d productos del productor principal.' %
                len(products))

        # Update/duplicate available products to create the final offer
        producers = models.Producer.objects.filter(active=True)

        for producer in producers:
            self.stdout.write(
                'Comprobando productor: %s...' %
                producer.company_name)

            producer_next_dist_date = \
                libs.get_producer_next_distribution_date(producer.id, False)

            # If this producer is not available in the next dist date, skip it
            if producer_next_dist_date != next_dist_date:
                self.stdout.write(
                    """Para este productor, la proxima fecha de """
                    """distribucion es: %s, saltando el productor.""" %
                    producer_next_dist_date.strftime('%d/%m/%Y'))
                continue

            self.stdout.write('Creando oferta del productor.')

            producer_last_dist_date = \
                libs.get_producer_last_distribution_date(producer.id, True)
            limit_date = \
                libs.get_producer_order_limit_date(producer, next_dist_date)

            # Choose the products with empty distribution dates
            products = models.Product.objects.filter(
                category__producer=producer,
                distribution_date__isnull=True,
                archived=False)

            if products:
                self.stdout.write(
                    'El productor tiene %d productos...' %
                    len(products))

                # Delete all products already copied for this week
                models.Product.objects.filter(
                    category__producer=producer,
                    distribution_date=next_dist_date,
                    sent_to_producer=False).delete()

                # Update fields and save as new record
                with transaction.atomic():
                    for product in products:
                        # If producer has fixed products, clear the primary key
                        # so that product is duplicated
                        # Else, product is overwritten
                        if producer.fixed_products:
                            product.pk = None

                        product.order_limit_date = limit_date
                        product.distribution_date = next_dist_date

                        # For producers with limited availability, copy
                        # the average ratings from last distribution
                        if producer.limited_availability:
                            prev_product = models.Product.objects.filter(
                                category__producer=producer,
                                distribution_date=producer_last_dist_date,
                                name=product.name,
                                origin=product.origin).first()

                            if prev_product:
                                product.average_rating = \
                                    prev_product.average_rating
                            else:
                                product.average_rating = 0
                                product.new_product = True
                        # For other producers, ratings will be updated
                        # automatically when products are rated
                        else:
                            product.average_rating = 0

                            # If there is not any product with same name and
                            # origin from last week
                            prev_product = models.Product.objects.filter(
                                category__producer=producer,
                                distribution_date=producer_last_dist_date,
                                name=product.name,
                                origin=product.origin)

                            # Mark product as new
                            if prev_product.count() == 0:
                                product.new_product = True

                        product.save()

                self.stdout.write(
                    'Los productos se han definido correctamente.')

        # Send the reminder email to the active members
        self.stdout.write(
            """Enviando el correo de informacion sobre la oferta """
            """a los miembros...""")

        # Prepare the offer summary with short explanation of each
        # available producer
        offer_summary = ""
        producers = models.Producer.objects.filter(
            category__product__order_limit_date__gt=libs.get_now()).distinct()

        for producer in producers:
            # Add information of these products to the offer summary included
            # in the email sent to members
            limit_date = \
                libs.get_producer_order_limit_date(producer, next_dist_date)
            offer_summary += \
                '<li>%s (fins %s)</li>' % \
                (producer.short_product_explanation,
                 timezone.localtime(limit_date).strftime("%d/%m/%Y %H:%M"))

        email_subject = '[BroquilGotic]Oferta d\'aquesta setmana'
        html_content = \
            """<p style="text-align: center;">""" \
            """<strong><u>El Bróquil Del Gótic</u></strong>""" \
            """</p>""" \
            """<p style="text-align: left; ">Hola broquilire!!!!</p>""" \
            """<p style="text-align: left; ">Aquesta setmana pots comprar """ \
            """aquests maravellosos productes!:</p>""" \
            """<h4 style="text-align: left; ">""" \
            """<b>[[CONTENT]]</b>""" \
            """</h4>""" \
            """<p style="text-align: left;">Ja pots fer la teva""" \
            """<strong>comanda</strong>""" \
            """<a href="https://el-broquil.rhcloud.com">aquí</a></p>"""

        offer_summary = "<ul>" + offer_summary + "</ul>"

        # If there is an email template stored in DB, use it
        email = models.EmailTemplate.objects.filter(
            email_code=models.EMAIL_OFFER_CREATED).first()

        if email:
            self.stdout.write(
                """OFERTA CREADA email plantilla encontrada en el base """
                """de datos.""")
            email_subject = email.full_subject()
            html_content = email.body

        # Fill in the email with offer summary and send to active users
        html_content = html_content.replace("[[CONTENT]]", offer_summary)

        result = libs.send_email_to_active_users(email_subject, html_content)

        self.stdout.write(
            'OFERTA CREADA email enviado a %d personas.' %
            result[0])
        os.remove(excel_file_path)

    def download_cal_rosset_excel(self):
        counter = 0
        # Directory where to save attachments (default: current)
        detach_dir = '/Users/onur/github/broquil/data/temp/'

        if 'OPENSHIFT_DATA_DIR' in os.environ:
            detach_dir = os.path.join(os.environ['OPENSHIFT_DATA_DIR'], "temp")

        email_subject = "oferta cal rosset"

        # Check offer emails sent in the last 5 days
        limit = datetime.now() - timedelta(days=5)

        # Connect to the Gmail IMAP server
        user = settings.EMAIL_HOST_USER
        pwd = settings.EMAIL_HOST_PASSWORD

        self.stdout.write('>Connectando a GMAIL')
        m = imaplib.IMAP4_SSL("imap.gmail.com")
        m.login(user, pwd)

        # Choose the default mailbox (Inbox)
        # m.select()

        # Choose the "All mail" folder
        m.select('"[Gmail]/Tots els missatges"')

        # Search for the offer emails (subject='oferta cal rosset' and
        # sent in the last few days)
        resp, items = m.search(
            None,
            '(SUBJECT "%s") (SINCE "%s")' %
            (email_subject, limit.strftime('%d-%b-%Y')))
        items = items[0].split()  # getting the mails id

        file_path = ""

        if len(items) == 0:
            self.stderr.write(
                '>No email en la bandeja de entrada con el TEMA: "%s".' %
                email_subject)
            return ""

        self.stdout.write(
            """>%d emails encontrados en la bandeja de entrada """
            """con el tema "%s".""" %
            (len(items), email_subject))

        for emailid in items:
            # Get the email
            resp, data = m.fetch(emailid, "(RFC822)")
            email_body = data[0][1]
            mail = email.message_from_string(email_body)

            # Only process mails with attachments
            if mail.get_content_maintype() != 'multipart':
                continue

            # Iterate over mail parts
            for part in mail.walk():
                # Multipart are just containers, so we skip them
                if part.get_content_maintype() == 'multipart':
                    continue

                # Is this part an attachment ?
                if part.get('Content-Disposition') is None:
                    continue

                # Get attachment filename
                filename = part.get_filename()

                # If there is no filename, we create one with a counter
                # to avoid duplicates
                if not filename:
                    filename = 'part-%03d%s' % (counter, 'bin')
                    counter += 1

                file_path = os.path.join(detach_dir, filename)

                self.stdout.write('Saving file %s.' % filename)
                # finally write the stuff
                fp = open(file_path, 'wb')
                fp.write(part.get_payload(decode=True))
                fp.close()

        return file_path
