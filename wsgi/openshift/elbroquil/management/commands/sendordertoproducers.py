# -*- coding: utf-8 -*-
from datetime import date, datetime, timedelta
from django.utils import timezone

from django.db import transaction
from django.db.models import F, Q, Sum, Count
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.utils.translation import ugettext as _

from decimal import Decimal
import email, imaplib, os
import html2text

import elbroquil.models as models
import elbroquil.libraries as libs
import elbroquil.parse as parser

class Command(BaseCommand):
    help = 'Sends the order to the producers'

    def handle(self, *args, **options):
        self.stdout.write('Executed task "send order to producers"')
        
        # Select active producers
        producers = models.Producer.objects.filter(active=True)
        
        # Were there any orders that were processed in this run?
        some_orders_processed = False

        next_dist_date = libs.get_next_distribution_date()
        
        # For each producer defined in the system
        for producer in producers:
            # Get the products which have exceeded their order limit dates 
            # and which are not yet sent to the producer
            products = models.Product.objects.filter(order_limit_date__lt=libs.get_now(), sent_to_producer=False, category__producer=producer).order_by('category__sort_order', 'id')
            
            # If there are no products, continue
            if len(products) == 0:
                continue
            
            # If these products belong to the next distribution date
            # Mark this variable so that later on we may decide to send emails to cooperative members
            # informing that their orders were sent
            if products[0].distribution_date == next_dist_date:
                some_orders_processed = True
            
            order_total = 0
            
            # Calculate total ordered quantity for each product
            for product in products:
                total_quantity = models.Order.objects.filter(product=product).aggregate(Sum('quantity'))['quantity__sum'] or Decimal(0)
                product.total_quantity = total_quantity
                product.arrived_quantity = total_quantity
                product.save()
                
                order_total += product.price * total_quantity
                
            # If producer has a defined minimum order, and it is not exceeded
            # or simply there was no order
            if (producer.minimum_order and order_total < producer.minimum_order) or order_total == 0:
                # Update the product quantities and set order status
                products.update(total_quantity=Decimal(0), arrived_quantity=Decimal(0), sent_to_producer=True)
                models.Order.objects.filter(product__in=products).update(status=models.STATUS_MIN_ORDER_NOT_MET)
                
                # Inform producer that there minimum order was not met
                email_subject = '[BroquilGotic]Aquest cop no arribem al mínim per a fer la comanda'
                html_content = 'Ho sentim molt'
                
                # If there is an email template stored in DB, use it
                email = models.EmailTemplate.objects.filter(email_code=models.EMAIL_PRODUCER_NO_ORDER).first()
                
                if email:
                    self.stdout.write('NO ORDER email template found in database.')
                    email_subject = email.full_subject()
                    html_content = email.body
                    
                send_email_to_address(email_subject, html_content, producer.email)
                
                # Skip to next producer
                continue
            
            # Prepare and send the email to the producer
            email_subject = '[BroquilGotic]Comanda del Broquil del Gòtic'
            html_content = '[[CONTENT]]'

            # If there is an email template stored in DB, use it
            email = models.EmailTemplate.objects.filter(email_code=models.EMAIL_PRODUCER_ORDER_TOTAL).first()
            if email:
                 self.stdout.write('ORDER TOTAL email template found in database.')
                 email_subject = email.full_subject()
                 html_content = email.body
                 
            order_totals_table = '<table border="1" cellpadding="2" cellspacing="0"><tr><th>Producte</th><th>Quantitat</th></tr>'
            
            for product in products:
                if product.total_quantity > 0:
                    order_totals_table += '<tr><td>' + product.name + '</td><td>' + str(product.total_quantity) + '</td></tr>'
            
            order_totals_table += '</table>'
            
            # Fill in the email with offer summary and send to active users
            html_content = html_content.replace("[[CONTENT]]", order_totals_table)
            libs.send_email_to_address(email_subject, html_content, [producer.email])
            products.update(sent_to_producer=True)
            
        # If some orders were processed in this run
        if some_orders_processed:
            # Check if there are any remaining products for this distribution date
            products = models.Product.objects.filter(sent_to_producer=False, distribution_date=next_dist_date)
            
            # If there are no remaining products, send the emails to the members
            if len(products) == 0:
                email_subject = '[BroquilGotic]S\'ha fet la comanda!!'
                html_content = '<p>S\'ha fet la comanda, pots passar a recollirla el Dimecres.</p><p>[[CONTENT]]</p><p>Salut!! amb el broquil :P<br></p>'

                # If there is an email template stored in DB, use it
                email = models.EmailTemplate.objects.filter(email_code=models.EMAIL_ORDER_SENT_TO_PRODUCER).first()
                if email:
                     self.stdout.write('ORDER SENT TO PRODUCER email template found in database.')
                     email_subject = email.full_subject()
                     html_content = email.body
                
                extra_information = ''
                # TODO ADD INFORMATION ABOUT PRODUCTS FOR WHICH MIN ORDER WAS NOT MET!
                #'Malauradament, no hem fet prou Encarrecs per demanar els seguents productes:'
                
                html_content = html_content.replace("[[CONTENT]]", extra_information)
                
                result = libs.send_email_to_active_users(email_subject, html_content)

                self.stdout.write('"Order sent to producer" email sent to %d people.' % result[0])
                