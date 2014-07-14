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

'''Page to enable users update/place their orders'''
@login_required
def update_order(request, category_no=''):
    '''Choose the available categories:
        - having products with dist. date in the future
        - not archived
    '''
    categories = models.Product.objects.filter(archived=False, order_limit_date__gt=date.today().strftime('%Y-%m-%d')).distinct('category').values('category__id', 'category__name', 'category__visible_name')

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
                    order.arrived_quantity = order.quantity
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
    category_name = categories[current_category-1]['category__visible_name'] or categories[current_category-1]['category__name'].title()
    next_category_name = ''

    if previous_category:
        prev_category_name = categories[previous_category-1]['category__visible_name'] or categories[previous_category-1]['category__name'].title()

    if next_category:
        next_category_name = categories[next_category-1]['category__visible_name'] or categories[next_category-1]['category__name'].title()


    products = zip(products, product_orders)

    progress = int(100*current_category/len(categories))

    return render(request, 'order/update_order.html', {
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
        total_price = (order.arrived_quantity*order.product.price).quantize(Decimal('.01'))
        totals.append(total_price)
        sum += total_price
        
    available_product_count = models.Product.objects.filter(archived=False, order_limit_date__gt=date.today().strftime('%Y-%m-%d')).count()

    orders_with_totals = zip(orders, totals)
    return render(request, 'order/view_order.html', {
          'orders_with_totals': orders_with_totals,
          'overall_sum': sum,
          'available_product_count': available_product_count,
      })

