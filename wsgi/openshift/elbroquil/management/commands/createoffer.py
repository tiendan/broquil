# -*- coding: utf-8 -*-
from datetime import date, datetime, timedelta
from django.utils import timezone

from django.db import transaction
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.utils.translation import ugettext as _

from decimal import Decimal
import email, imaplib, os
import html2text
import xlrd
import settings

import elbroquil.models as models
import elbroquil.libraries as libs
import elbroquil.parse as parser


class Command(BaseCommand):
    help = 'Crea la oferta y informa los miembros activos'

    def handle(self, *args, **options):
        # Check if there will be an offer this week (exclude today in case it is Wednesday)
        next_dist_date = libs.get_next_distribution_date(False)

        days_until_next_distribution = (next_dist_date - libs.get_today()).days

        #self.stdout.write('Para Cal Rosset, la proxima fecha de distribucion es: ' + next_dist_date.strftime('%d/%m/%Y') + '.')

        # If there is more than one week until next distribution date, do not create offer
        if days_until_next_distribution > 7:
            self.stdout.write('Quedan ' + days_until_next_distribution + ' dias para la proxima fecha de distribucion ('"+next_dist_date.strftime('%d/%m/%Y')+"'). NO se creara la oferta.')
            return
        
        # Update/duplicate available products to create the final offer
        producers = models.Producer.objects.filter(active=True)

        for producer in producers:
            self.stdout.write('Comprobando productor: ' + producer.company_name + "...")
            producer_next_dist_date = libs.get_producer_next_distribution_date(producer.id, False)

            # If this producer is not available in the next dist date, skip it
            if producer_next_dist_date != next_dist_date:
                self.stdout.write('Para este productor, la proxima fecha de distribucion es: ' + producer_next_dist_date.strftime('%d/%m/%Y') + ', saltando el productor.')
                continue

            self.stdout.write('Creando oferta del productor.')

            producer_last_dist_date = libs.get_producer_last_distribution_date(producer.id, True)
            limit_date = libs.get_producer_order_limit_date(producer, next_dist_date)

            # Choose the products with empty distribution dates
            products = models.Product.objects.filter(category__producer=producer, distribution_date__isnull=True, archived=False)

            if products:
                self.stdout.write('El productor tiene ' + str(len(products)) + ' productos...')
                
                # Delete all products already copied for this week
                models.Product.objects.filter(category__producer=producer, distribution_date=next_dist_date,sent_to_producer=False).delete()

                # Update fields and save as new record
                with transaction.atomic():
                    for product in products:
                        # If producer has fixed products, clear the primary key so that product is duplicated
                        # Else, product is overwritten
                        if producer.fixed_products:
                            product.pk = None

                        product.order_limit_date = limit_date
                        product.distribution_date = next_dist_date

                        # For producers with limited availability, copy the average ratings from last distribution
                        if producer.limited_availability:
                            prev_product = models.Product.objects.filter(category__producer=producer, distribution_date=producer_last_dist_date, name=product.name, origin=product.origin).first()

                            if prev_product:
                                product.average_rating = prev_product.average_rating
                            else:
                                product.average_rating = 0
                                product.new_product = True
                        # For other producers, ratings will be updated automatically when products are rated
                        else:
                            product.average_rating = 0

                            # If there is not any product with same name and origin from last week
                            prev_product = models.Product.objects.filter(category__producer=producer, distribution_date=producer_last_dist_date, name=product.name, origin=product.origin)

                            # Mark product as new
                            if prev_product.count() == 0:
                                product.new_product = True

                        product.save()

                self.stdout.write('Los productos se han definido correctamente.')

        # Send the reminder email to the active members
        self.stdout.write('Enviando el correo de informacion sobre la oferta a los miembros...')

        # Prepare the offer summary with short explanation of each available producer
        offer_summary = ""
        producers = models.Producer.objects.filter(category__product__order_limit_date__gt=libs.get_now()).distinct()
        for producer in producers:
            # Add information of these products to the offer summary included in the email sent to members
            limit_date = libs.get_producer_order_limit_date(producer, next_dist_date)
            offer_summary += "<li>" + producer.short_product_explanation + " (fins " + timezone.localtime(limit_date).strftime("%d/%m/%Y %H:%M") + ")</li>"
                
        email_subject = '[BroquilGotic]Oferta d\'aquesta setmana'
        html_content = '<p style="text-align: center;"><strong><u>El Bróquil Del Gótic</u></strong></p><p style="text-align: left; ">Hola broquilire!!!!</p><p style="text-align: left; ">Aquesta setmana pots comprar aquests maravellosos productes!:</p><h4 style="text-align: left; "><b>[[CONTENT]]</b></h4><p style="text-align: left;">Ja pots fer la teva <strong>comanda</strong> <a href="https://el-broquil.rhcloud.com">aquí</a></p><p>PARTICIPA!!!</p><p>El Bróquil funciona gràcies al treball voluntari de tots nosaltres, pel que et demanem:</p><ul><li>Apunta\'t a les <strong>permanències</strong>: pots fer-ho a l\'enllaç de dalt o a la pestanya del document de comandes.</li><li>Apunta\'t a les comissions: enviant un correu als referents de les <strong>comissions</strong>. Sobretot si no pots fer permanències, <strong>hi ha altres maneres de participar</strong>. Te les indiquem <u>aquí mateix</u>.</li></ul><p></p><p><strong>Enllaços útils</strong>: <a href="http://elbroquildelgotic.blogspot.com.es/p/contacto.html">Triptic de benvinguda</a>, <a href="http://elbroquildelgotic.blogspot.com.es/p/blog-page_30.html">Manual de Permanències</a> / <a href="http://elbroquildelgotic.blogspot.com.es/p/blog-page.html">Manual per a fer comandes</a>.</p><p><strong>COM FER LA COMANDA</strong></p><ul><li><strong>Omplir la comanda</strong>: La comanda es pot omplir <strong>fins al diumenge a les 24h</strong>, per tal de poder reenviar-la a temps als productors. Assegureu-vos d\'omplir la vostra comanda en la columna amb el vostre nom.</li><li><strong>Productes</strong>: Els <strong>productes</strong> es compren per <strong>pes, manats o unitats i pes</strong> (és el cas dels melons, carabasses, síndria i similars que es demanen per unitats peró es paguen per pes )</li><li><strong>Recollida de la comanda</strong>: La comanda es recull els <strong>dimecres de 18:30h a 20:00h</strong> a c. <strong>Nou de Sant Francesc, 21</strong>. Sigueu puntuals! Penseu en portar <strong>bosses, carro o cistella</strong> per a emportar-vos la comanda.</li><li><strong>Quota de transport</strong>: La quota és de <strong>12èeuro;</strong> per trimestre, que s\'abona al començament de cada trimestre natural.</li></ul><p></p><p>El Bróquil del Gótic <a href="http://elbroquildelgotic.blogspot.com.es/">Blog</a> <br>Espai social del Gótic La negreta<br>c. Nou de Sant Francesc 21<br>Barcelona 08002<br>93 315 18 20 (dimecres de 18 a 20 h)</p>'

        offer_summary = "<ul>" + offer_summary + "</ul>"

        # If there is an email template stored in DB, use it
        email = models.EmailTemplate.objects.filter(email_code=models.EMAIL_OFFER_CREATED).first()

        if email:
            self.stdout.write('OFERTA CREADA email plantilla encontrada en el base de datos.')
            email_subject = email.full_subject()
            html_content = email.body

        # Fill in the email with offer summary and send to active users
        html_content = html_content.replace("[[CONTENT]]", offer_summary)

        # Add the Gmail action link (yet to see if it works)
        html_content += """<div itemscope itemtype="http://schema.org/EmailMessage">
        <div itemprop="action" itemscope itemtype="http://schema.org/ViewAction">
        <link itemprop="url" href="http://el-broquil.rhcloud.com"></link>
        <meta itemprop="name" content="Fer Comanda"></meta>
        </div>
        <meta itemprop="description" content="Fer Comanda"></meta>
        </div>"""

        result = libs.send_email_to_active_users(email_subject, html_content)

        self.stdout.write('OFERTA CREADA email enviado a %d personas.' % result[0])
        os.remove(excel_file_path)
