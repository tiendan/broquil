# -*- coding: utf-8 -*-
from decimal import Decimal
import ast
import xlrd
import logging      # import the logging library
from datetime import date

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required, permission_required
from django.core.urlresolvers import reverse
from django.db.models import F, Q, Sum
from django.db import transaction

from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.utils import translation
from django.views.generic import FormView
#from django.core.urlresolvers import resolve
#from django.template import RequestContext
from django.utils import timezone


import elbroquil.models as models
from elbroquil.forms import UploadProductsForm, CheckProductsForm
import elbroquil.parse as parser
import elbroquil.libraries as libs

'''Get an instance of a logger'''
logger = logging.getLogger("MYAPP")

'''Page to upload Excel files to define products'''
@login_required
@permission_required('elbroquil.modify_products')
def upload_products(request):
    form = UploadProductsForm()

    return render(request, 'product/upload_products.html', {
        'form': form,
    })
   
'''Page to check the parsed product information from the Excel files''' 
@login_required
@permission_required('elbroquil.modify_products')
def check_products(request):
    products = []
    producer_id = ""
    
    '''If the form is submitted, parse the Excel file and show on page'''
    if request.method == 'POST':
        '''Read posted form'''
        form = UploadProductsForm(request.POST, request.FILES)
        
        if form.is_valid():
            '''Open Excel workbook and read the related parameters (producer and Excel file format)'''
            book = xlrd.open_workbook(form.cleaned_data['excel_file'].name, file_contents=form.cleaned_data['excel_file'].read())
            
            producer_id = form.cleaned_data['producer'].id
            excel_format = form.cleaned_data['producer'].excel_format
            logger.error("Check Products")
            logger.error("PRODUCER ID: " + str(producer_id))
            logger.error("EXCEL FORMAT: " + str(excel_format))
            '''Choose the appropriate parsing function depending on file format'''
            if excel_format == models.CAL_ROSSET:
                products = parser.parse_cal_rosset(book)
            elif excel_format == models.CAN_PIPI:
                products = parser.parse_can_pipirimosca(book)
            
            return render(request, 'product/check_product_info.html', {
                'products': products,
                'producer': producer_id
            })
        else:
            '''If form not valid, render the form page again'''
            return render(request, 'product/upload_products.html', {
                'form': form,
            })
    else:
        '''If nothing is posted, redirect to Excel upload page'''
        return HttpResponseRedirect(reverse('elbroquil.views.upload_products', args=()))
        
'''After parsed product information is verified, this view adds them to database'''
@login_required
@permission_required('elbroquil.modify_products')
def confirm_products(request):
    products = []

    '''If the form is submitted, read the verified information and create the products'''
    if request.method == 'POST':
        form = CheckProductsForm(request.POST)
        form.is_valid()
        table_data = ast.literal_eval(form.cleaned_data['table_data'])
        producer_id = form.cleaned_data['producer_id']
        producer = models.Producer.objects.get(id=producer_id)
        
        with transaction.atomic():
            '''Delete old products from the same producer'''
            models.Product.objects.filter(distribution_date=None, category__producer_id=producer_id).delete()
            
            '''Insert new products one by one'''
            for product_info in table_data:
                category_text = product_info[0]
                name_text = product_info[1]
                price_text = product_info[2].replace(',', '.')
                unit_text = product_info[3]
                origin_text = product_info[4]
                comments_text = product_info[5]
            
                '''Clean the unit text and remove currency char and extra chars'''
                unit_text = unit_text.replace('€', '').replace('*', '').replace('/', '').strip()
                
                '''If comments include the word unitat, or the unit is not kilos
                    the demand should be made in units
                '''
                integer_demand = "unitat" in comments_text.lower() or unit_text.lower() != "kg"
                
                for exceptional_product in [u"carabassa", u"síndria", u"meló"]:
                    integer_demand = integer_demand or exceptional_product in name_text.lower()
                
                category, created = models.Category.objects.get_or_create(name=category_text, producer_id=producer_id)
            
                prod = models.Product(name=name_text, category_id=category.id, origin=origin_text, comments=comments_text, price=Decimal(price_text), unit=unit_text, integer_demand=integer_demand)
                prod.save()
        
        return HttpResponseRedirect(reverse('elbroquil.views.view_products', args=(producer_id,)))
    
    return HttpResponseRedirect(reverse('elbroquil.views.upload_products', args=()))
        
@login_required
@permission_required('elbroquil.modify_products')
def view_products(request, producer_id=''):
    #return HttpResponseRedirect(reverse('admin:elbroquil_producer_change', args=(producer_id,)))
    products = []
    
    if request.method == 'POST':
        producer_id = request.POST['producer_id']
    
    if producer_id != '':
        products = models.Product.objects.filter(distribution_date=None, category__producer_id=int(producer_id)).order_by('category__sort_order', 'id')
        
    producers = models.Producer.objects.all().order_by('company_name')

    '''If there are no products with dist_date=None, choose the ones where dist_date>now'''
    if len(products) == 0 and producer_id != '':
        products = models.Product.objects.filter(Q(distribution_date__gt=libs.get_today()), category__producer_id=int(producer_id)).order_by('category__sort_order', 'id')
    
    add_category_row = []
    prev_category = ''

    for prod in products:
      if prod.category.name != prev_category:
          add_category_row.append(True)
          prev_category = prod.category.name
      else:
          add_category_row.append(False)

    if producer_id != '':
        producer_id = int(producer_id)
    
    products = zip(products, add_category_row)
    return render(request, 'product/view_defined_products.html', {
        'products': products,
        'producers': producers,
        'producer_id': producer_id,
    })

