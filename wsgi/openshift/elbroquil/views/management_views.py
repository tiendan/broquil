# -*- coding: utf-8 -*-
from decimal import Decimal
import logging      # import the logging library
from datetime import date, datetime, timedelta

from django.contrib import admin
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db.models import F, Q, Sum, Count
from django.db import transaction

from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.utils import translation
from django.views.generic import FormView


import elbroquil.models as models


@login_required
#@permission_required('elbroquil.accounting')   ONUR: Accounting page open to everyone
def view_distribution_detail(request):
    # Form fields
    only_latest_dates = True
    selected_date = None
    date_texts = []
    date_values = []
    detail_records = models.DistributionAccountDetail.objects.all().order_by("-date")
    
    not_arrived_product_list = []
    amount_changed_product_list = []
    
    # Account summary values
    initial_cash = 0
    member_consumed_amount = 0
    debt_balance = 0
    collected_amount = 0
    quarterly_fee_collected_amount = 0
    final_amount = 0
    expected_final_amount = 0
    large_final_difference = False
    
    producer_payments = []
    
    # Read post variables
    if request.method == 'POST':
        selected_date = request.POST.get("date")
        only_latest_dates = request.POST.get("only-latest") is not None
        
        if selected_date != "-1":
            # Choose the list of ordered products (total quantity > 0)
            products = models.Product.objects.filter(archived=False, distribution_date=selected_date, total_quantity__gt=0).order_by('category__sort_order', 'name')
        
            # Separate the products according to their status
            for product in products:
                if product.total_quantity == product.arrived_quantity:  # No incidents
                    pass
                elif product.arrived_quantity == 0:
                    not_arrived_product_list.append(product)            # Did not arrive
                else:
                    amount_changed_product_list.append(product)         # Amount changed
                    
            # Load accounting summary information
            record = models.DistributionAccountDetail.objects.filter(date=selected_date).first()
            
            if record:
                initial_cash = record.initial_amount
                member_consumed_amount = record.member_consumed_amount
                debt_balance = record.debt_balance_amount
                collected_amount = record.total_member_payment_amount
                quarterly_fee_collected_amount = record.quarterly_fee_collected_amount
                final_amount = record.final_amount
                expected_final_amount = record.expected_final_amount
                
                # If there's a gap of more than 5 euros, show the expected amount in red
                large_final_difference = abs(expected_final_amount - final_amount) > 5
                
                # Load producer payments
                producer_payments = models.ProducerPayment.objects.filter(date=selected_date)
        else:
            selected_date = 0
                
    
    # Store latest few dates in variable
    for detail in detail_records:
        date_texts.append(detail.date)
        date_values.append(detail.date.strftime("%Y-%m-%d"))
        
        # Limit to latest 10 dates
        if only_latest_dates and len(date_texts) >= 10:
            break
    
    distribution_dates = zip(date_texts, date_values)
    
    return render(request, 'management/view_distribution_detail.html', {
        'selected_date': selected_date,
        'only_latest_dates': only_latest_dates,
        'distribution_dates': distribution_dates,
        'not_arrived_product_list': not_arrived_product_list,
        'amount_changed_product_list': amount_changed_product_list,
        
        'initial_cash': initial_cash,
        'collected_amount': collected_amount,
        'member_consumed_amount': member_consumed_amount,
        'debt_balance': debt_balance,
        'quarterly_fee_collected_amount': quarterly_fee_collected_amount,
        
        'final_amount': final_amount,
        'expected_final_amount': expected_final_amount,
        'large_final_difference': large_final_difference,

        'producer_payments': producer_payments,
    })
    