# -*- coding: utf-8 -*-
from decimal import Decimal
import ast
import xlrd
import logging      # import the logging library
from datetime import date

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
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


import elbroquil.models as models
from elbroquil.forms import UploadProductsForm, UpdateOrderForm, CheckProductsForm
import elbroquil.parse as parser

'''Get an instance of a logger'''
logger = logging.getLogger("MYAPP")
     
@login_required
def view_product_orders(request, product_no=''):
    #products = models.Product.objects.filter(Q(archived=False), Q(distribution_date=date.today().strftime('%Y-%m-%d')),Q(order__isnull=False)).distinct('category__sort_order', 'id', 'name').order_by('category__sort_order', 'id')

    products = models.Product.objects.filter(archived=False, distribution_date=date.today().strftime('%Y-%m-%d'),arrived_quantity__gt=0).order_by('category__sort_order', 'id')
     
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

        # Delete old orders and insert new ones
        with transaction.atomic():
            orders = models.Order.objects.filter(product_id=current_product_id)
            
            for o in orders:
                key = "order_arrived_"+str(o.id)
                item = request.POST.get(key).strip()
                
                if len(item) > 0:
                    '''Update the arrived quantity and status'''
                    o.arrived_quantity = Decimal(item.replace(',', '.'))
                    
                    if o.arrived_quantity == 0:
                        o.status = models.STATUS_DID_NOT_ARRIVE
                    else:
                        o.status = models.STATUS_NORMAL
                    
                    o.save()

    product_orders = models.Order.objects.filter(product__id=current_product_id).order_by('user__first_name', 'user__last_name')

    total_quantity = 0
    total_arrived_quantity = 0
    
    for i in range(0, len(product_orders)):
        total_quantity = total_quantity + product_orders[i].quantity
        total_arrived_quantity = total_arrived_quantity + product_orders[i].arrived_quantity
      
    prev_product_name = ''
    product_name = products[current_product-1].name
    next_product_name = ''
    
    if previous_product:
        prev_product_name = products[previous_product-1].name

    if next_product:
        next_product_name = products[next_product-1].name
        
    progress = int(80*current_product/len(products))
        
    return render(request, 'distribution/view_product_orders.html', {
       'product_orders': product_orders,
       'current_product_id': current_product_id,
       
       'product_name': product_name,
       'prev_product_name': prev_product_name,
       'next_product_name': next_product_name,
       
       'current_product_no': current_product,
       'prev_product_no': previous_product,
       'next_product_no': next_product,
       
       'total_quantity': total_quantity,
       'total_arrived_quantity': total_arrived_quantity,
       'progress': progress,
    })
    

@login_required
def view_order_totals(request):
    #products = models.Product.objects.filter(Q(archived=False), Q(distribution_date__gt=date.today().strftime('%Y-%m-%d')), Q(order__isnull=False)).annotate(total_order=Sum('order__quantity')).order_by('category__sort_order', 'id')
    
    products = models.Product.objects.filter(archived=False, distribution_date=date.today().strftime('%Y-%m-%d'),total_quantity__gt=0).order_by('category__sort_order', 'id')
    
    add_category_row = []
    prev_category = ''
    
    
    '''If the form was submitted'''
    if request.method == 'POST':
        with transaction.atomic():
            for product in products:
                key = "product_arrived_"+str(product.id)
                item = request.POST.get(key).strip()
                
                if len(item) > 0:
                    '''Update the arrived quantity and status'''
                    product.arrived_quantity = Decimal(item.replace(',', '.'))
                    product.save()
                    
                    '''If product arrived quantity is marked as 0, mark the product orders too. Also do the reverse'''
                    if product.arrived_quantity == 0:
                        models.Order.objects.filter(product_id=product.id).update(arrived_quantity=0, status=models.STATUS_DID_NOT_ARRIVE)
                    else:
                        models.Order.objects.filter(product_id=product.id).update(arrived_quantity=F('quantity'), status=models.STATUS_NORMAL)
    
    for prod in products:
        if prod.category.name != prev_category:
            add_category_row.append(True)
            prev_category = prod.category.name
        else:
            add_category_row.append(False)
        
    products = zip(products, add_category_row)
    return render(request, 'distribution/view_order_totals.html', {
          'products': products,
      })

