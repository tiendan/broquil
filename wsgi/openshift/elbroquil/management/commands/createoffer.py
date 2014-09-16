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
        offer_summary = "" 
        
        # Check if there will be an offer this week
        next_dist_date = libs.get_next_distribution_date()
        
        days_until_next_distribution = (next_dist_date - libs.get_today()).days
        
        # If there is more than one week until next distribution date, do not create offer
        if days_until_next_distribution > 7:
            self.stdout.write('Quedan ' + days_until_next_distribution + ' dias para la proxima fecha de distribucion ('"+next_dist_date.strftimeime('%d/%m/%Y')+"'). NO se creara la oferta.')
            return
        
        # Fetch Cal Rosset excel file from Gmail and get the local file path
        self.stdout.write('Intentando descargar el excel de Cal Rosset...') 
        excel_file_path = self.download_cal_rosset_excel()
        
        if excel_file_path == "":
            self.stderr.write('Problema al descargar el excel de Cal Rosset.')
            return
            
        self.stdout.write('El excel se ha descargado correctamente.')
        
        # Get Cal Rosset producer record, read the excel and parse the products
        cal_rosset = models.Producer.objects.filter(excel_format=models.CAL_ROSSET).first()
        book = xlrd.open_workbook(excel_file_path)
        products = parser.parse_cal_rosset(book)
        
        # In a transaction
        with transaction.atomic():
            # Delete old products from the same producer
            models.Product.objects.filter(distribution_date=None, category__producer_id=cal_rosset.id).delete()
            
            # Insert new products one by one
            for product in products:
                category_text = product[0]
                name_text = product[1]
                price_text = str(product[2]).replace(',', '.')
                unit_text = product[3]
                origin_text = product[4]
                comments_text = product[5]
            
                # Clean the unit text and remove currency char and extra chars
                unit_text = unit_text.replace(u'€', '').replace('*', '').replace('/', '').strip()
                
                # If comments include the word unitat, or the unit is not kilos
                # the demand should be made in units
                integer_demand = "unitat" in comments_text.lower() or unit_text.lower() != "kg"
                
                # For some exceptional products, update the integer_demand value
                for exceptional_product in [u"carabassa", u"síndria", u"meló"]:
                    integer_demand = integer_demand or exceptional_product in name_text.lower()
                
                category, created = models.Category.objects.get_or_create(name=category_text, producer_id=cal_rosset.id)
            
                # Create and save the product
                prod = models.Product(name=name_text, category_id=category.id, origin=origin_text, comments=comments_text, price=Decimal(price_text), unit=unit_text, integer_demand=integer_demand)
                prod.save()
                
            self.stdout.write('Se han importado %d productos de Cal Rosset.' % len(products))
        
        # Update/duplicate available products to create the final offer
        producers = models.Producer.objects.filter(active=True)
        
        for producer in producers:
            self.stdout.write('Comprobando productor: ' + producer.company_name + "...")
            producer_next_dist_date = libs.get_producer_next_distribution_date(producer.id)
            
            # If this producer is not available in the next dist date, skip it
            if producer_next_dist_date != next_dist_date:
                self.stdout.write('Para este productor, la proxima fecha de distribucion es: ' + producer_next_dist_date.strftimeime('%d/%m/%Y') + ', saltando el productor.')
                continue
            
            self.stdout.write('Creando oferta del productor.')
            
            producer_last_dist_date = libs.get_producer_last_distribution_date(producer.id)
            limit_date = libs.get_producer_order_limit_date(producer, next_dist_date)
            
            # Choose the products with empty distribution dates
            products = models.Product.objects.filter(category__producer=producer, distribution_date__isnull=True)
            
            if products:
                self.stdout.write('El productor tiene ' + str(len(products)) + ' productos...')
                
                # Add information of these products to the offer summary included in the email sent to members
                offer_summary += "<li>" + producer.short_product_explanation + " (" + _(u'until') + " " + limit_date.strftimeime("%d/%m/%Y %H:%M") + ")</li>"
                
                # Delete all products already copied for this week
                models.Product.objects.filter(category__producer=producer, distribution_date=next_dist_date).delete()
                
                # Update fields and save as new record
                with transaction.atomic():
                    for product in products:
                        # If producer has fixed products, clear the primary key so that product is duplicated
                        # Else, product is overwritten
                        if producer.fixed_products:
                            product.pk = None
                    
                        product.order_limit_date = limit_date
                        product.distribution_date = next_dist_date
                        
                        # Get the average rating for this product from previous weeks
                        prev_product = models.Product.objects.filter(category__producer=producer, distribution_date=producer_last_dist_date, name=product.name, origin=product.origin).first()
                        
                        if prev_product:
                            product.average_rating = prev_product.average_rating
                        else:
                            product.average_rating = 0
                            product.new_product = True
                        
                        product.save()
                
                self.stdout.write('Los productos se han definido correctamente.')
        
        # Send the reminder email to the active members
        self.stdout.write('Enviando el correo de informacion sobre la oferta a los miembros...')
                
        email_subject = '[BroquilGotic]Oferta d\'aquesta setmana'
        html_content = '<p style="text-align: center;"><strong><u>El Bróquil Del Gótic</u></strong></p><p style="text-align: left; ">Hola broquilire!!!!</p><p style="text-align: left; ">Aquesta setmana pots comprar aquests maravellosos productes!:</p><h4 style="text-align: left; "><b>[[CONTENT]]</b></h4><p style="text-align: left;">Ja pots fer la teva <strong>comanda</strong> <a href="https://docs.google.com/spreadsheet/ccc?key=tFyzm2cnCXD1gK_B84p_zGQ">aquí</a></p><p style="text-align: left;">I apuntar-te <a href="https://docs.google.com/spreadsheet/ccc?key=tFyzm2cnCXD1gK_B84p_zGQ">aquí</a> a les <strong>permanències</strong></p><p>PARTICIPA!!!</p><p>El Bróquil funciona gràcies al treball voluntari de tots nosaltres, pel que et demanem:</p><ul><li>Apunta\'t a les <strong>permanències</strong>: pots fer-ho a l\'enllaç de dalt o a la pestanya del document de comandes.</li><li>Apunta\'t a les comissions: enviant un correu als referents de les <strong>comissions</strong>. Sobretot si no pots fer permanències, <strong>hi ha altres maneres de participar</strong>. Te les indiquem <u>aquí mateix</u>.</li></ul><p></p><p><strong>Enllaços útils</strong>: <a href="http://elbroquildelgotic.blogspot.com.es/p/contacto.html">Triptic de benvinguda</a>, <a href="http://elbroquildelgotic.blogspot.com.es/p/blog-page_30.html">Manual de Permanències</a> / <a href="http://elbroquildelgotic.blogspot.com.es/p/blog-page.html">Manual per a fer comandes</a>.</p><p><strong>COM FER LA COMANDA</strong></p><ul><li><strong>Omplir la comanda</strong>: La comanda es pot omplir <strong>fins al diumenge a les 24h</strong>, per tal de poder reenviar-la a temps als productors. Assegureu-vos d\'omplir la vostra comanda en la columna amb el vostre nom.</li><li><strong>Productes</strong>: Els <strong>productes</strong> es compren per <strong>pes, manats o unitats i pes</strong> (és el cas dels melons, carabasses, síndria i similars que es demanen per unitats peró es paguen per pes )</li><li><strong>Recollida de la comanda</strong>: La comanda es recull els <strong>dimecres de 18:30h a 20:00h</strong> a c. <strong>Nou de Sant Francesc, 21</strong>. Sigueu puntuals! Penseu en portar <strong>bosses, carro o cistella</strong> per a emportar-vos la comanda.</li><li><strong>Quota de transport</strong>: La quota és de <strong>12èeuro;</strong> per trimestre, que s\'abona al començament de cada trimestre natural.</li></ul><p></p><p>El Bróquil del Gótic <a href="http://elbroquildelgotic.blogspot.com.es/">Blog</a> <br>Espai social del Gótic La negreta<br>c. Nou de Sant Francesc 21<br>Barcelona 08002<br>93 315 18 20 (dimecres de 18 a 20 h)</p>'
        
        offer_summary = "<ul>" + offer_summary + "</ul>"
        
        # If there is an email template stored in DB, use it
        email = models.EmailTemplate.objects.filter(email_code=models.EMAIL_OFFER_CREATED).first()
        
        if email:
            self.stdout.write('OFERTA CREADA email plantilla encontrada en el base de datos.')
            email_subject = email.full_subject()
            html_content = email.body
        
        # Fill in the email with offer summary and send to active users
        html_content = html_content.replace("[[CONTENT]]", offer_summary)
        
        result = libs.send_email_to_active_users(email_subject, html_content)
        
        self.stdout.write('OFERTA CREADA email enviado a %d personas.' % result[0])
        
        
    def download_cal_rosset_excel(self):
        # Directory where to save attachments (default: current)
        detach_dir = '/Users/onur/ultim/data/temp/'
        
        if os.environ.has_key('OPENSHIFT_DATA_DIR'):
            detach_dir = os.path.join(os.environ['OPENSHIFT_DATA_DIR'], "temp")
        
        email_subject = "oferta cal rosset"
        
        # Check offer emails sent in the last 5 days
        limit = datetime.now() - timedelta(days=5)

        # Connect to the Gmail IMAP server
        user = settings.EMAIL_HOST_SECONDARY_USER
        pwd = settings.EMAIL_HOST_SECONDARY_PASSWORD 
        
        self.stdout.write('>Connectando a GMAIL')
        m = imaplib.IMAP4_SSL("imap.gmail.com")
        m.login(user,pwd)
        
        # Choose the default mailbox (Inbox)
        m.select()
        
        # Search for the offer emails (subject='oferta cal rosset' and sent in the last few days)
        resp, items = m.search(None, '(SUBJECT "'+email_subject+'") (SINCE "'+limit.strftimeime('%d/%m/%Y')+'")')
        items = items[0].split() # getting the mails id
        
        file_path = ""
        
        if len(items) == 0:
            self.stderr.write('>No email en la bandeja de entrada con el TEMA: "%s".' % email_subject)
            return ""
        
        
        self.stdout.write('>%d emails encontrados en la bandeja de entrada con el tema "%s".' % [len(items), email_subject])
        
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

                # If there is no filename, we create one with a counter to avoid duplicates
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
        
