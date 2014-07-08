# -*- coding: utf-8 -*-
from decimal import Decimal
import ast
import xlrd
import logging      # import the logging library

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db.models import Q, Sum
from django.db import transaction

from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.utils import translation
from django.views.generic import FormView
#from django.core.urlresolvers import resolve
#from django.template import RequestContext


import elbroquil.models as models
from elbroquil.forms import UploadProductsForm, UpdateOrderForm, CheckProductsForm
import elbroquil.parse as parser

'''Get an instance of a logger'''
logger = logging.getLogger("MYAPP")

'''Page to upload Excel files to define products'''
@login_required
def upload_products(request):
    form = UploadProductsForm()

    return render(request, 'upload_products.html', {
        'form': form,
    })
   
'''Page to checked the parsed product information from the Excel files''' 
@login_required
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
            
            return render(request, 'check_product_info.html', {
                'products': products,
                'producer': producer_id
            })
        else:
            '''If form not valid, render the form page again'''
            return render(request, 'upload_products.html', {
                'form': form,
            })
    else:
        '''If nothing is posted, redirect to Excel upload page'''
        return HttpResponseRedirect(reverse('elbroquil.views.upload_products', args=()))
        
'''After parsed product information is verified, this view adds them to database'''
@login_required
def confirm_products(request):
    products = []
    producer_id = None

    '''If the form is submitted, read the verified information and create the products'''
    if request.method == 'POST':
        form = CheckProductsForm(request.POST)
        form.is_valid()
        table_data = ast.literal_eval(form.cleaned_data['table_data'])
        producer_id = form.cleaned_data['producer_id']
    
        for product_info in table_data:
            category_text = product_info[0]
            name_text = product_info[1]
            price_text = product_info[2]
            unit_text = product_info[3]
            origin_text = product_info[4]
            comments_text = product_info[5]
            
            '''Clean the unit text and remove currency char and extra chars'''
            unit_text = unit_text.replace('€', '').replace('*', '').replace('/', '').strip()
            
            category, created = models.Category.objects.get_or_create(name=category_text, producer_id=producer_id)
            
            prod = models.Product(name=name_text, category_id=category.id, origin=origin_text, comments=comments_text, price=Decimal(price_text), unit=unit_text)
            prod.save()
        
        return HttpResponseRedirect(reverse('admin:shop_producer_change', args=(producer_id,)))
    else:
        '''If nothing is posted, redirect to Excel upload page'''
        return HttpResponseRedirect(reverse('elbroquil.views.upload_products', args=()))
    
    return HttpResponseRedirect(reverse('admin:shop_producer_changelist', args=()))
        
        
'''Page to enable users update/place their orders'''
@login_required
def update_order(request, category_no=''):
    '''Choose the available categories:
        - having products with dist. date in the future (TODO CHANGE TO: next wednesday)
        - not archived
    '''
    categories = models.Product.objects.filter(archived=False, distribution_date__gt='2014-03-05').distinct('category').values('category__id', 'category__name', 'category__visible_name')
    
    '''Choose the indices for the current, previous and next categories'''
    previous_category = None
    current_category = None
    next_category = None
    current_category_id = None
    
    '''If no category chosen, choose the first one as default and second one as next'''
    if category_no == '' and len(categories) > 0:
        current_category = 1
        if len(categories) > 1:
            next_category = 2
    else:
        '''If given category no is outside bounds, give 404'''
        current_category = int(category_no)
        if current_category > len(categories) or current_category < 1:
            raise Http404
        
        if current_category > 1:
            previous_category = current_category - 1
                
        if current_category < len(categories):
            next_category = current_category + 1
    
    '''Get current category id'''
    current_category_id = categories[current_category-1]['category__id']
    
    if request.method == 'POST': # If the form has been submitted...
        #form = UpdateOrderForm([], request.POST) # A form bound to the POST data
        
        # Delete old orders and insert new ones
        with transaction.atomic():
            products = models.Product.objects.filter(distribution_date__isnull=False, archived=False, category_id=current_category_id)
            models.Order.objects.filter(user=request.user, archived=False, product__category=current_category_id).delete()
        
            for p in products:
                key = "product_"+str(p.id)
                item = request.POST.get(key).strip()
                if len(item) > 0:
                    logger.error("ITEM: " + key)
                    order = models.Order()
                    order.product = p
                    order.user = request.user
                    order.quantity = Decimal(item.replace(',', '.'))
                    order.save()
    
    products = models.Product.objects.filter(Q(category_id=current_category_id), Q(distribution_date__isnull=False), Q(archived=False)).order_by('id')
    user_orders = models.Order.objects.filter(product__category_id=current_category_id, archived=False, user=request.user).order_by('product__id')
    
    order_index = 0
    product_orders = []
    for i in range(0, len(products)):
        if order_index < len(user_orders) and products[i].id == user_orders[order_index].product.id:
            product_orders.append(user_orders[order_index].quantity)
            order_index = order_index+1
        else:
            product_orders.append(None)
    
    prev_category_name = ''
    category_name = categories[current_category-1]['category__visible_name']
    next_category_name = ''

    if previous_category:
        prev_category_name = categories[previous_category-1]['category__visible_name']

    if next_category:
        next_category_name = categories[next_category-1]['category__visible_name']


    products = zip(products, product_orders)
    
    progress = int(100*current_category/len(categories))
    
    return render(request, 'update_order.html', {
         'products': products,
         
         'category_name': category_name,
         'prev_category_name': prev_category_name,
         'next_category_name': next_category_name,
         
         'category_no': current_category,
         'prev_category_no': previous_category,
         'next_category_no': next_category,
         
         'progress': progress,
     })
     

@login_required
def view_order(request):
    orders = models.Order.objects.filter(user=request.user, archived=False).prefetch_related('product').order_by('product__category__sort_order', 'product__name')
    totals = []
    sum = 0
    
    for order in orders:
        total_price = (order.quantity*order.product.price).quantize(Decimal('.01'))
        totals.append(total_price)
        sum += total_price

    orders_with_totals = zip(orders, totals)
    return render(request, 'view_order.html', {
          'orders_with_totals': orders_with_totals,
          'overall_sum': sum,
      })


@login_required
def view_product_orders(request, product_no=''):
    products = models.Product.objects.filter(Q(archived=False), Q(distribution_date__gt='2014-03-05'),Q(order__isnull=False)).distinct('category__sort_order', 'id', 'name').order_by('category__sort_order', 'id')
     
    previous_product = None
    current_product = None
    next_product = None
    current_product_id = None

    # If no product chosen, choose the first one as default and second one as next
    if product_no == '' and len(products) > 0:
        logger.error("Product no empty!!")
        current_product = 1
        if len(products) > 1:
            next_product = 2
    else:
        current_product = int(product_no)
        
        if current_product > 1:
            previous_product = current_product-1

        if current_product < len(products):
            next_product = current_product + 1

    if current_product is None:
      raise Http404
      
    current_product_id = products[current_product-1].id

    if request.method == 'POST': # If the form has been submitted...
        #for field in form.cleaned_data['producer']
        logger.error("Form POSTed")
        logger.error(request.POST)

        # Delete old orders and insert new ones
        with transaction.atomic():
            # TODO UPDATE DB
            pass

    product_orders = models.Order.objects.filter(product__id=current_product_id).order_by('user__first_name', 'user__last_name')

    total_quantity = 0
    
    for i in range(0, len(product_orders)):
        total_quantity = total_quantity + product_orders[i].quantity
      
    prev_product_name = ''
    product_name = products[current_product-1].name
    next_product_name = ''
    
    if previous_product:
        prev_product_name = products[previous_product-1].name

    if next_product:
        next_product_name = products[next_product-1].name
        
    progress = int(80*current_product/len(products))
        
    return render(request, 'view_product_orders.html', {
       'product_orders': product_orders,
       'current_product_id': current_product_id,
       
       'product_name': product_name,
       'prev_product_name': prev_product_name,
       'next_product_name': next_product_name,
       
       'current_product_no': current_product,
       'prev_product_no': previous_product,
       'next_product_no': next_product,
       
       'total_quantity': total_quantity,
       'progress': progress,
    })
    

@login_required
def view_order_totals(request):
    products = models.Product.objects.filter(Q(archived=False), Q(distribution_date__gt='2014-03-05'), Q(order__isnull=False)).annotate(total_order=Sum('order__quantity')).order_by('category__sort_order', 'id')
    
    add_category_row = []
    prev_category = ''
    
    for prod in products:
        if prod.category.name != prev_category:
            add_category_row.append(True)
            prev_category = prod.category.name
        else:
            add_category_row.append(False)
        
    products = zip(products, add_category_row)
    return render(request, 'view_order_totals.html', {
          'products': products,
      })

def set_language(request):
    #current_url = resolve(request.POST.get(next).strip()).url_name
    #logger.error("CURRENT URL")
    #logger.error(current_url)
    
    user_language = request.GET['language'] or 'ca'
    translation.activate(user_language)
    request.session['django_language'] = user_language
    
    #logger.error("NEXT URL")
    #logger.error(reverse(current_url, args=()))
    
    return HttpResponseRedirect(reverse('site_root'))
