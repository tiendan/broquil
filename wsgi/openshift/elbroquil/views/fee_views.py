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
#from django.core.urlresolvers import resolve
#from django.template import RequestContext


import elbroquil.models as models
import elbroquil.parse as parser


@login_required
@permission_required('elbroquil.accounting')
def view_fees(request):
    # Read the user list
    users = User.objects.filter(is_superuser=False).order_by('first_name', 'last_name')
    quarterly_fees = models.Quarterly.objects.all().order_by('-year', '-quarter')
    
    selected_member = -1
    selected_quarter = "-1"
    selected_quarter_year = -1
    selected_quarter_quarter = -1
    
    quarters = []
    filtered_quarterly_fees = []
    member_fees = []
    
    previous_year = -1
    previous_quarter = -1
    
    if request.method == 'POST':
        form_name = request.POST.get("form-name").strip()
        
        if form_name == "quarter-form":
            selected_quarter = request.POST.get("quarter")
            
            # Extract year and quarter from "selected_quarter" (with format 2012_3)
            selected_quarter_year = int(selected_quarter.split('_')[0])
            selected_quarter_quarter = int(selected_quarter.split('_')[1])
            
            filtered_quarterly_fees = models.Quarterly.objects.filter(year=selected_quarter_year, quarter=selected_quarter_quarter).prefetch_related('user', 'payment').order_by('user__first_name', 'user__last_name')
            
        elif form_name == "member-form":
            selected_member = int(request.POST.get("member_id"))
            
            member_fee_history = models.Quarterly.objects.filter(user_id=selected_member).order_by('year', 'quarter')
            
            member_fee_years = []
            member_fee_quarters = []
            
            # A really expensive, but yet more easily understandable way to do this
            if len(member_fee_history):
                initial_year = member_fee_history[0].year
                final_year = member_fee_history[len(member_fee_history)-1].year
                
                # For each year in the history
                for current_year in range(initial_year, final_year+1):
                    year_fees = []
                    
                    # For each quarter, get the (if existing) payment and add it to year_fees 
                    for current_quarter in range(1, 5):
                        year_fees.append(models.Quarterly.objects.filter(user_id=selected_member, year=current_year, quarter=current_quarter).first())
                        
                    member_fee_years.append(current_year)
                    member_fee_quarters.append(year_fees)
                
            member_fees = zip(member_fee_years, member_fee_quarters)    
    
    for fee in quarterly_fees:
        if fee.year != previous_year or fee.quarter != previous_quarter:
            quarters.append(fee)
            previous_year = fee.year
            previous_quarter = fee.quarter
    
    return render(request, 'fee/view_fees.html', {
          'users': users,
          'quarters': quarters,
          'selected_member': selected_member,
          'selected_quarter': selected_quarter,
          
          'selected_quarter_year': selected_quarter_year,
          'selected_quarter_quarter': selected_quarter_quarter,
          
          'filtered_quarterly_fees': filtered_quarterly_fees,
          'member_fees': member_fees
    })
    
    
        

@login_required
@permission_required('elbroquil.accounting')
def create_fees(request):
    alert_message = None
    
    # Read the user list
    users = User.objects.filter(is_superuser=False).order_by('first_name', 'last_name')
    
    # Write down the year and the quarter for the fee to be generated
    year = date.today().year
    quarter = (date.today().month/3) + 1
    
    if quarter > 5:
        quarter = 1
        year = year+1
        
    if request.method == 'POST':
        # Else, delete old fees and insert new ones
        member_ids = request.POST.getlist('user_ids')
        fee_amount = request.POST.get('fee_amount').strip()
    
        # Search for already paid fees for this year&quarter
        paid_fees = models.Quarterly.objects.filter(year=year, quarter=quarter, payment__isnull=False, user__in=member_ids)
    
        if len(paid_fees) > 0:
            # If there is already a payment, user cannot create fees again
            alert_message = _(u"Someone has alread paid the fee for this quarter! You cannot delete them!")
        elif len(member_ids) == 0:
            alert_message = _(u"Please choose members")
        elif fee_amount == '':
            alert_message = _(u"Please enter fee amount")
        else:
            with transaction.atomic():
                models.Quarterly.objects.filter(year=year, quarter=quarter, user__in=member_ids).delete()
            
                for member_id in member_ids:
                    fee = models.Quarterly(user_id=member_id, year=year, quarter=quarter, amount=Decimal(fee_amount.replace(',', '.')))
                    fee.save()
    
    
    return render(request, 'fee/create_fees.html', {
          'users': users,
          'alert_message': alert_message,
          'year': year,
          'quarter': quarter
      })
        