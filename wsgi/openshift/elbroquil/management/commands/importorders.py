# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
import elbroquil.models as models
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.core.mail import EmailMultiAlternatives
from django.core.exceptions import ObjectDoesNotExist
import html2text
import email, os
import random

import elbroquil.libraries as libs

import urllib2
import xlrd
from decimal import Decimal

class Command(BaseCommand):
    help = 'Importa los pedidos del excel de Encarrecs'

    def handle(self, *args, **options):
        self.stdout.write('Importando los pedidos del excel de Encarrecs ')
        
        detach_dir = '/Users/onur/ultim/data/temp/'
        
        if os.environ.has_key('OPENSHIFT_DATA_DIR'):
            detach_dir = os.path.join(os.environ['OPENSHIFT_DATA_DIR'], "temp")
            
        file_path = os.path.join(detach_dir, "encarrecs.xlsx")
        
        myfile = urllib2.urlopen("https://docs.google.com/spreadsheet/pub?key=tFyzm2cnCXD1gK_B84p_zGQ&output=xls")
        output = open(file_path, 'wb')
        output.write(myfile.read())
        output.close()
        
        book = xlrd.open_workbook(file_path)
        sheet = book.sheet_by_index(0)
        
        row_count = sheet.nrows
        col_count = sheet.ncols
        
        num_members_with_order = 0

        # Iterate over all members
        for member_column in range(5, col_count-4, 2):
            member_name = sheet.cell_value(rowx=0, colx=member_column)
            member_total_order = sheet.cell_value(rowx=row_count-1, colx=member_column+1)
            
            # If member has an order
            if member_total_order > 0:
                self.stdout.write(member_name)
                num_members_with_order += 1
                
                # Find or create the user object
                member = User.objects.filter(first_name=member_name)
                
                if not member:
                    self.stdout.write('Miembro no encontrado, creando nuevo usuario ')
                    
                    member = User()
                    member.username = 'user' + str(random.randint(100, 100000))
                    member.first_name = member_name
                    member.last_name = ""
                    
                    # Calculate a valid email address
                    valid_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                    member.email = 'tiendan+' + ''.join(c for c in member.username.lower() if c in valid_chars) + "@gmail.com"
                    
                    member.set_password("1111")
                    member.save()
                else:
                    member = member.first()
                
                # Add the orders for this user
                next_dist_date = libs.get_next_distribution_date()
                
                models.Order.objects.filter(user=member, product__distribution_date=next_dist_date).delete()
                
                for product_row in range(4, row_count-2):
                    price = sheet.cell_value(rowx=product_row, colx=0)
                    
                    # Skip unrelated rows
                    if price == '' or str(price).startswith('%%'):
                        continue
                    
                    price = Decimal(price).quantize(Decimal('.0001'))
                    product_name = sheet.cell_value(rowx=product_row, colx=2)
                    member_order = sheet.cell_value(rowx=product_row, colx=member_column)
                    
                    if member_order == '':
                        continue
                    
                    product = models.Product.objects.filter(name__startswith=product_name, distribution_date=next_dist_date)
                    
                    if product:
                        product = product.first()
                        
                        order = models.Order()
                        order.user = member
                        order.product = product
                        order.quantity = member_order
                        order.arrived_quantity = member_order
                        order.save()
                    else:
                        self.stdout.write('Producto no encontrado: ' + product_name)
                        
                    
                order_summary = libs.calculate_user_orders(member, next_dist_date)
                
                if abs(Decimal(member_total_order) - order_summary[1]) > 0.03:
                    self.stdout.write('Pedidos no corresponden: excel=' + str(member_total_order) + ', sistema=' + str(order_summary[1]))
                    
        
        self.stdout.write(str(num_members_with_order))
        