# -*- coding: utf-8 -*-
from decimal import Decimal
import logging      # import the logging library
from datetime import date, datetime, timedelta

from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.shortcuts import render
from django.utils.dateparse import *
from django.db.models import F, Q, Sum
from django.utils.translation import ugettext_lazy as _

import elbroquil.models as models
import elbroquil.libraries as libs

import settings, os

import httplib2
from oauth2client.client import SignedJwtAssertionCredentials
from httplib2 import Http
from apiclient.discovery import build


import json

@login_required
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
    
    # Store latest few dates in variable
    for detail in detail_records:
        if selected_date == None:
            selected_date = detail.date.strftime("%Y-%m-%d")
        
        date_texts.append(detail.date)
        date_values.append(detail.date.strftime("%Y-%m-%d"))
        
        # Limit to latest 10 dates
        if only_latest_dates and len(date_texts) >= 10:
            break
        
    if selected_date is not None and selected_date != "-1":
        # Choose the list of ordered products (total quantity > 0)
        products = models.Product.objects.filter(archived=False, distribution_date=selected_date, total_quantity__gt=0).order_by('category__sort_order', 'name')

        # Separate the products according to their status
        for product in products:
            if product.total_quantity == product.arrived_quantity:  # No incidents
                pass
            elif product.arrived_quantity == 0:
                not_arrived_product_list.append(product)            # Did not arrive
            else:
                # If product is ordered in units and charged in kg's, it's not an incident
                if product.unit == "kg" and product.integer_demand:
                    pass
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
    


@login_required
def view_distribution_task_information(request):
    # Form fields
    selected_year = libs.get_today().year
    yearly_tasks = []
    member_task_names = []
    member_task_counts = []
    member_summary = []
    add_month_row = []
    available_years = range(2015, (libs.get_today() + datetime.timedelta(60)).year+1)
    update_log = ""
    form_name = ""
    
    # Read post variables
    if request.method == 'POST':
        selected_year = int(request.POST.get("year"))
        form_name = request.POST.get("form-name").strip()

    # If "update-form" is submitted, re-read task information from calendar
    if form_name == "update-form":
        # TODO, only do this if user has permission
        update_log = update_distribution_task_information(selected_year)

    # Choose the list of tasks for the selected year
    distribution_tasks = models.DistributionTask.objects.filter(distribution_date__year = selected_year).prefetch_related('user').order_by('distribution_date')

    # Separate the products according to their status
    current_distribution_date = None
    current_task_members = []

    # Prepare the array containing [dist_date, members] pairs
    for task in distribution_tasks:
        member_full_name = task.user.first_name + " " + task.user.last_name

        # if member_full_name exists in member_task_names, update count in member_task_counts
        # else, append it to member_task_names and append count=1 to member_task_counts
        if member_full_name in member_task_names:
            member_index = member_task_names.index(member_full_name)
            member_task_counts[member_index] = member_task_counts[member_index] + 1
        else:
            member_task_names.append(member_full_name)
            member_task_counts.append(1)

        if task.distribution_date != current_distribution_date:
            if current_task_members:
                yearly_tasks.append([current_distribution_date, current_task_members])

            if current_distribution_date is None or current_distribution_date.month != task.distribution_date.month:
                add_month_row.append(True)
            else:
                add_month_row.append(False)

            current_task_members = []
            current_distribution_date = task.distribution_date

        current_task_members.append(member_full_name)

    # If there is one item still waiting to be added, append it
    if current_task_members:
        yearly_tasks.append([current_distribution_date, current_task_members])

        if current_distribution_date.month != yearly_tasks[-1][0].month:
            add_month_row.append(True)
        else:
            add_month_row.append(False)

    # order and zip member_task_names and member_task_counts
    indexes = range(len(member_task_counts))
    indexes.sort(key=member_task_counts.__getitem__, reverse=True)

    member_task_names2 = map(member_task_names.__getitem__, indexes)
    member_task_counts2 = map(member_task_counts.__getitem__, indexes)

    member_summary = zip(member_task_names2, member_task_counts2)

    yearly_tasks = zip(yearly_tasks, add_month_row)
            
    return render(request, 'management/view_distribution_task_information.html', {
        'selected_year': selected_year,
        'yearly_tasks': yearly_tasks,
        'member_summary': member_summary,
        'available_years': available_years,
        'update_log': update_log,
    })
    
# TODO ONUR @permission_required('elbroquil.update_dist_task')
def update_distribution_task_information(year):
    update_log = ""
    
    with transaction.atomic():
        # Directory where to find the private key
        data_dir = '/Users/onur/github/broquil/data/temp'

        if os.environ.has_key('OPENSHIFT_DATA_DIR'):
            data_dir = os.path.join(os.environ['OPENSHIFT_DATA_DIR'], "temp")

        # Setup the connection to Google Calendar API
        client_email = '975533004012-d4veh1666grh6es8bq0celae34u9ag7k@developer.gserviceaccount.com'
        with open(os.path.join(data_dir, "serviceaccount.json")) as f:
            private_key = json.load(f)['private_key']

        credentials = SignedJwtAssertionCredentials(client_email, private_key,
            ['https://www.googleapis.com/auth/sqlservice.admin', 'https://www.googleapis.com/auth/calendar'])

        http_auth = credentials.authorize(Http())
        service = build('calendar', 'v3', http=http_auth)

        year_beginning = str(year) + "-01-01T00:00:00Z"
        request = service.events().list(calendarId='lt3p1poe2spctu4u9vogokk59g@group.calendar.google.com', timeMin=year_beginning)

        
        # Delete old task objects for the given year
        models.DistributionTask.objects.filter(distribution_date__year = year).delete()
        print "Deleted old tasks"
        
        # Loop until all pages have been processed.
        while request != None:
            # Get the next page.
            response = request.execute()
            for event in response.get('items', []):
                print "Another event"
                distribution_date = event.get("start","").get("dateTime", "")
                
                # Continue with next iteration if dist date not valid
                if distribution_date == "":
                    continue
                
                distribution_date = parse_date(distribution_date[0:10])
                date_string = distribution_date.strftime('%d/%m/%Y')
                
                task_members = []
                
                for attendee in event.get('attendees', []):
                    current_email = attendee.get('email', "")
                    
                    # Continue with next iteration if email not valid (or it is admin email)
                    if current_email == "" or current_email == "broquilgotic@gmail.com":
                        continue        
                    
                    # Find user for this email
                    user = models.User.objects.filter(email=current_email, is_active=True).first()
                    
                    # If not found, try the secondary email too
                    if not user:
                        extra_info = models.ExtraInfo.objects.filter(secondary_email=current_email, user__is_active=True).first()
                        
                        if extra_info:
                            user = extra_info.user
                        else:
                            message = _(u"Could not find member with email:") + ""
                            update_log = update_log + "<br>" + date_string + " " + message + " " + current_email
                            continue
                        
                    # If the user is already added to the event, skip 
                    if user in task_members:
                        message = _(u"Member exists twice in event, email:") + ""
                        update_log = update_log + "<br>" +  date_string + " " + message + " " + current_email
                        continue
                
                    # Add the user to the event
                    task = models.DistributionTask(distribution_date=distribution_date, user=user)
                    task.save()
                    
                    task_members.append(user)
            
            # Get the next request object by passing the previous request object to
            # the list_next method.
            request = service.events().list_next(request, response)
    
    print "Transaction finished successfully"
    return update_log

@login_required
def view_accounting_detail(request):
    start_date = None
    end_date = None
    
    if request.method == 'POST':
        start_date = request.POST.get("start-date").strip()
        end_date = request.POST.get("end-date").strip()
    else:
        # By default, show last two months
        today = libs.get_today()
        
        start_date = today.strftime("%d/%m/%Y")
        end_date = (today - datetime.timedelta(60)).strftime("%d/%m/%Y")
    
    # Create the accounting summary information
    # Convert dates from posted format to DB format (+ time)
    start_date_formatted = start_date[6:11] + "-" + start_date[3:5] + "-" + start_date[0:2] + " 00:00:00"
    end_date_formatted = end_date[6:11] + "-" + end_date[3:5] + "-" + end_date[0:2] + " 23:59:59"

    # TODO CONTINUE
    # Fetch records from distr. information and acc. movements
    # Iterate at the same time respecting the chronology
    # Fill a 2D array with the information to display on the page
    #   Date, before, after, comment, before, after, explanation
    
    return render(request, 'management/view_accounting_detail.html', {
            'start_date' : start_date,
            'end_date' : end_date,
    })