# -*- coding: utf-8 -*-
from decimal import Decimal
import ast
import xlrd
import logging      # import the logging library
from datetime import date, datetime, timedelta

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required, permission_required
from django.core.mail import EmailMessage
from django.core.urlresolvers import reverse
from django.db.models import F, Q, Sum, Avg
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
import elbroquil.parse as parser

import elbroquil.libraries as libs

'''Get an instance of a logger'''
logger = logging.getLogger("MYAPP")

'''Page to enable users update/place their orders'''
@login_required
def update_order(request, category_no=''):
    '''Choose the available categories:
        - having products with order limit date in the future
        - not archived
    '''
    categories = models.Category.objects.filter(product__archived=False, product__order_limit_date__gt=libs.get_now()).distinct()

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
    current_category_id = categories[current_category-1].pk

    if request.method == 'POST': # If the form has been submitted...
        # Delete old orders and insert new ones
        with transaction.atomic():
            products = models.Product.objects.filter(distribution_date__gt=libs.get_today(), archived=False, category_id=current_category_id)
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
        
        # Recalculate the order summary
        libs.calculate_order_summary(request)
        
    products = models.Product.objects.filter(Q(category_id=current_category_id), Q(distribution_date__isnull=False), Q(order_limit_date__gt=libs.get_now()), Q(archived=False)).order_by('id')
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
    category_name = categories[current_category-1].visible_name or categories[current_category-1].name.title()
    next_category_name = ''

    if previous_category:
        prev_category_name = categories[previous_category-1].visible_name or categories[previous_category-1].name.title()

    if next_category:
        next_category_name = categories[next_category-1].visible_name or categories[next_category-1].name.title()


    products = zip(products, product_orders)

    progress = int(100*current_category/len(categories))
    
    if not request.session.get('order_total'):
        libs.calculate_order_summary(request)
        
    few_hours_later = libs.get_now() + timedelta(hours=4)
    a_day_later = libs.get_now() + timedelta(days=1)

    return render(request, 'order/update_order.html', {
         'products': products,
     
         'category_name': category_name,
         'prev_category_name': prev_category_name,
         'next_category_name': next_category_name,
     
         'category_no': current_category,
         'prev_category_no': previous_category,
         'next_category_no': next_category,
     
         'progress': progress,
         
         'few_hours_later': few_hours_later,
         'a_day_later': a_day_later,

         'order_total': request.session['order_total'],
         'order_summary': request.session['order_summary'],
     })
 

@login_required
def view_order(request):
    today = libs.get_today()
    all_orders = models.Order.objects.filter(user=request.user, archived=False, product__distribution_date__gte=today).prefetch_related('product').order_by('product__category__sort_order', 'product__name')
    next_dist_date = libs.get_next_distribution_date()
    totals = []
    orders = []
    rest_of_orders = []
    debt = 0
    quarterly_fee = 0
    sum = 0

    for order in all_orders:
        if order.product.distribution_date != next_dist_date:
            rest_of_orders.append(order)
        else:
            orders.append(order)
            total_price = (order.arrived_quantity*order.product.price).quantize(Decimal('.01'))
            totals.append(total_price)
            sum += total_price
        
    available_product_count = models.Product.objects.filter(archived=False, order_limit_date__gt=libs.get_now()).count()
    
    orders_with_totals = zip(orders, totals)
    
    # Get debt from last weeks (if exists)
    last_debt = models.Debt.objects.filter(user_id=request.user, payment__date__lt=today).order_by('-payment__date').first()
    
    if last_debt is not None:
        debt = last_debt.amount
        
    quarterly = models.Quarterly.objects.filter(Q(user=request.user), Q(created_date__gt = today - timedelta(days=60)), Q(payment__isnull=True) | Q(payment__date=today) ).first()
    
    if quarterly is not None:
        quarterly_fee = quarterly.amount
        
    sum = sum + debt + quarterly_fee
    
    if not request.session.get('order_total'):
        libs.calculate_order_summary(request)
        
    
    return render(request, 'order/view_order.html', {
          'orders_with_totals': orders_with_totals,
          'overall_sum': sum,
          'debt': debt,
          'quarterly_fee': quarterly_fee,
          'available_product_count': available_product_count,
          'rest_of_orders': rest_of_orders,
          
          'order_total': request.session['order_total'],
          'order_summary': request.session['order_summary'],
      })

@login_required
def rate_products(request):
    # Only rate products that were distributed in the last 5 days
    today = libs.get_today()
    limit_date = today - timedelta(days=5)

    orders = models.Order.objects.filter(user=request.user, archived=False, status=models.STATUS_NORMAL, product__distribution_date__gte=limit_date, product__distribution_date__lte=today).prefetch_related('product').order_by('product__category__sort_order', 'product__name')

    if request.method == 'POST': # If the form has been submitted...
        for order in orders:
            key = "rating-" + str(order.id)
            rating = request.POST.get(key)
            
            if rating is not None and int(rating) > 0:
                order.rating = int(rating)
                order.save()
            else:
                order.rating = None
                order.save()
            
            # Update product average rating
            order.product.average_rating = models.Order.objects.filter(product=order.product, archived=False, status=models.STATUS_NORMAL, rating__isnull=False).aggregate(Avg('rating'))['rating__avg'] or 0
            order.product.save()
    
            # No need to reload results as we overwrite the only changed column
    
    if not request.session.get('order_total'):
        libs.calculate_order_summary(request)
    
    return render(request, 'order/rate_products.html', {
          'orders': orders,

          'order_total': request.session['order_total'],
          'order_summary': request.session['order_summary'],
      })
      
def test_email(request):
    # TODO Check other parameters from https://docs.djangoproject.com/en/1.6/topics/email/#emailmessage-objects
    email = EmailMessage('Dummy subject', 'This is my beautiful email body', to=['tiendan@gmail.com'])
    email.send()
    