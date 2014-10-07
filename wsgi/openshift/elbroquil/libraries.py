from decimal import Decimal
import ast
import pickle

from datetime import date, datetime, timedelta

from django.db import transaction
from django.db.models import F, Q, Sum

from django.utils import translation, timezone
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.views.generic import FormView
from django.core.urlresolvers import reverse

import elbroquil.models as models

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.core.mail import EmailMultiAlternatives
from django.core.exceptions import ObjectDoesNotExist
import html2text

from pytz import timezone as pytztimezone
import settings

# Calculates the order summary for the user (when there is an update in the order)
# Only the products for the next distribution date are counted and the results are
# saved in the session as an HTML string in the session. These results are later shown
# on the dropdown order summary on order pages.
def calculate_order_summary(request):
    today = get_today()
    dist_date = get_next_distribution_date()
    shown_item_count = 5
    
    # Get the orders for next distribution date and for this user
    orders = models.Order.objects.filter(user=request.user, archived=False, product__distribution_date=dist_date, status=models.STATUS_NORMAL).prefetch_related('product').order_by('-quantity', 'product__name')
    
    order_summary = '<table class="table table-condensed summary-table">'
    debt = 0
    quarterly_fee = 0
    order_total = 0
    i = 1
    
    if len(orders) > 0:
        order_summary = order_summary + "<thead><tr><th>" + _(u"PRODUCTS") + "</th></tr></thead><tbody>"
        
        for order in orders:
            total_price = (order.arrived_quantity*order.product.price).quantize(Decimal('.01'))
            
            # For the first "n" items, include the name of product, for the rest, just include "... more products" summary
            if i <= shown_item_count:
                order_summary = order_summary + "<tr><td>" + order.product.name + "</td></tr>"
            elif i == shown_item_count + 1:
                order_summary = order_summary + "<tr><td><a href='" + reverse('elbroquil.views.view_order') + "'>" + _(u'And') + " " + str(len(orders)-shown_item_count) + " " + _(u'more products') + "</a></td></tr>"
            
            # Accumulate the total price to be shown in the dropdown toggle menu item
            order_total += total_price
            i += 1
            
        order_summary = order_summary + '</tbody></table>'
    else:
        order_summary = order_summary + "<tbody><tr><td>" + _(u"No products in cart") + "</td></tr></tbody></table>"
        
    # Get debt from last weeks (if exists) 
    last_debt = models.Debt.objects.filter(user_id=request.user, payment__date__lt=today).order_by('-payment__date').first()

    if last_debt is not None:
        debt = last_debt.amount

    # Get the quarterly fee to be paid (if exists)
    quarterly = models.Quarterly.objects.filter(Q(user=request.user), Q(created_date__gt = timezone.now() - timedelta(days=60)), Q(payment__isnull=True) | Q(payment__date=today) ).first()

    if quarterly is not None:
        quarterly_fee = quarterly.amount

    # Add the extra payments to the total and save results to the session
    order_total = order_total + debt + quarterly_fee
    
    request.session['order_total'] = str(order_total)
    request.session['order_summary'] = order_summary
    
# Calculate the date for the next wednesday
def get_next_wednesday(allow_today=True):
    # Get today
    day = get_today()
    
    # If today is not allowed (today may be wednesday and we want to get the next one)
    if not allow_today:
        day += timedelta(days=1)
    
    # While day of week is not Wednesday, add one 
    days_till_next_wednesday = (models.WEDNESDAY - day.weekday()) % 7
    day += timedelta(days=days_till_next_wednesday)
    
    return day

# Calculate the next distribution date
def get_next_distribution_date(allow_today=True):
    wednesday = get_next_wednesday(allow_today)
    
    # While the calculated date corresponds to a skipped date, get next week
    while models.SkippedDistributionDate.objects.filter(skipped_date=wednesday):
        wednesday += timedelta(days=7)
    
    return wednesday
    # return date(2014, 7, 29)


# Calculate the next distribution date for the given producer
def get_producer_next_distribution_date(producer_id, allow_today=True):
    producer = models.Producer.objects.get(pk=producer_id)
    wednesday = get_next_wednesday(allow_today)
    
    iterations = 1
    
    # While the calculated date corresponds to a skipped date,
    # or producer has limited availability and he/she is not available on that date
    #   get next week
    while models.SkippedDistributionDate.objects.filter(skipped_date=wednesday) \
            or (producer.limited_availability and not models.ProducerAvailableDate.objects.filter(available_date=wednesday)):
        wednesday += timedelta(days=7)
        
        # If there are no available dates in the next 5 weeks, return a date in the far far future
        if iterations > 5:
            return date(2040, 1, 1)
        
        iterations += 1
    
    
    return wednesday
    # return date(2014, 7, 29)


# Returns the last date when products were distributed
def get_last_distribution_date():
    last_distributed_product = models.Product.objects.all().order_by("-distribution_date").first()
    
    if last_distributed_product:
        return last_distributed_product.distribution_date
    else:
        return None


# Returns the last date when this producer's products were distributed
def get_producer_last_distribution_date(producer_id, allow_today=False):
    if allow_today:
        last_distributed_product = models.Product.objects.filter(category__producer_id=producer_id, distribution_date__lte=get_today()).order_by("-distribution_date").first()
    else:
        # Consider only products which were distributed at least 6 days ago
        # These are the ones which are closed for being rated
        distribution_limit = get_today() - timedelta(days=6)
        
        last_distributed_product = models.Product.objects.filter(category__producer_id=producer_id, distribution_date__lt=distribution_limit).order_by("-distribution_date").first()
    
    if last_distributed_product:
        return last_distributed_product.distribution_date
    else:
        return None


# Returns the order limit date for the given producer and given distribution date
def get_producer_order_limit_date(producer, next_dist_date):
    zone = pytztimezone(settings.TIME_ZONE)
    
    day = next_dist_date
    day = zone.localize(datetime(day.year, day.month, day.day, producer.order_hour), is_dst=False)
    
    days_to_substract = (next_dist_date.weekday() - producer.order_day) % 7
    day -= timedelta(days=days_to_substract)
    
    # Save the datetime in UTC timezone
    day = day.astimezone(pytztimezone("UTC"))
    
    return day


def get_today():
    #return date(2014, 8, 20)
    return timezone.now().astimezone(pytztimezone(settings.TIME_ZONE)).date()
    #return timezone.now().date()

def get_now():
    return timezone.now()

def send_email_to_active_users(subject, content):
    # Get list of active members
    active_users = User.objects.filter(is_superuser=False, is_active=True)
    bcc_list = []
    
    for user in active_users:
        # For each member, append the email to the BCC list
        bcc_list.append(user.email)
        
        # If member has secondary email, add it to BCC list too
        try:
            if user.extrainfo.secondary_email and len(user.extrainfo.secondary_email) > 0:
                bcc_list.append(user.extrainfo.secondary_email)
        except ObjectDoesNotExist:
            pass
    
    text_content = html2text.html2text(content)
    email = EmailMultiAlternatives(subject, text_content, bcc=bcc_list)
    email.attach_alternative(content, "text/html")
    email.send()

    return [len(bcc_list)]
    
def send_email_to_address(subject, content, to):
    text_content = html2text.html2text(content)
    email = EmailMultiAlternatives(subject, text_content, to=to)
    email.attach_alternative(content, "text/html")
    email.send()
