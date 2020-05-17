from datetime import date, datetime, timedelta
from decimal import Decimal
from pytz import timezone as pytztimezone
import json
import os

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMultiAlternatives
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import *
from django.utils.translation import ugettext as _

from httplib2 import Http
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

import elbroquil.models as models

import html2text
import project.settings as settings
import base64



# Calculates the order summary for the user (when there is an update in
# the order)
# Only the products for the next distribution date are counted and the results
# are saved in the session as an HTML string in the session. These results are
# later shown on the dropdown order summary on order pages.
def calculate_order_summary(request):
    today = get_today()
    dist_date = get_next_distribution_date()
    shown_item_count = 5

    # Get the orders for next distribution date and for this user
    orders = models.Order.objects.filter(
        user=request.user,
        archived=False,
        product__distribution_date=dist_date,
        status=models.STATUS_NORMAL) \
        .prefetch_related('product') \
        .order_by('-quantity', 'product__name')

    order_summary = '<table class="table table-condensed summary-table">'
    debt = 0
    quarterly_fee = 0
    order_total = Decimal(0)
    i = 1

    if len(orders) > 0:
        order_summary = order_summary + "<thead><tr><th>" + \
            _("PRODUCTS") + "</th></tr></thead><tbody>"

        for order in orders:
            total_price = (order.arrived_quantity *
                           order.product.price).quantize(Decimal('.0001'))

            # For the first "n" items, include the name of product, for the
            # rest, just include "... more products" summary
            if i <= shown_item_count:
                order_summary += "<tr><td>" + order.product.name + "</td></tr>"
            elif i == shown_item_count + 1:
                order_summary += "<tr><td><a href='" + reverse('view_order') \
                    + "'>" + _('And') + " " \
                    + str(len(orders) - shown_item_count) + " " \
                    + _('more products') + "</a></td></tr>"

            # Accumulate the total price to be shown in the dropdown toggle
            # menu item
            order_total += total_price
            i += 1

        order_summary = order_summary + '</tbody></table>'
    else:
        order_summary = order_summary + "<tbody><tr><td>" + \
            _("No products in cart") + "</td></tr></tbody></table>"

    # Get debt from last weeks (if exists)
    last_debt = models.Debt.objects.filter(
        user_id=request.user,
        payment__date__lt=today).order_by('-payment__date').first()

    if last_debt is not None:
        debt = last_debt.amount

    # Get the quarterly fee to be paid (if exists)
    quarterly = models.Quarterly.objects.filter(
        Q(user=request.user),
        Q(created_date__gt=timezone.now() - timedelta(days=60)),
        Q(payment__isnull=True) | Q(payment__date=today)).first()

    if quarterly is not None:
        quarterly_fee = quarterly.amount

    # Add the extra payments to the total and save results to the session
    order_total = order_total + debt + quarterly_fee

    request.session['order_total'] = str(order_total.quantize(Decimal('.01')))
    request.session['order_summary'] = order_summary


def calculate_user_orders(member, dist_date):
    # Get the orders for next distribution date and for this user
    orders = models.Order.objects.filter(
        user=member,
        product__distribution_date=dist_date,
        status=models.STATUS_NORMAL) \
        .prefetch_related('product') \
        .order_by('-quantity', 'product__name')

    order_total = 0
    product_count = 0

    if len(orders) > 0:
        for order in orders:
            product_price = (order.arrived_quantity *
                             order.product.price).quantize(Decimal('.0001'))

            order_total += product_price
            product_count += 1

    return [product_count, order_total]


# Calculate the date for the next weekday (by default FRIDAY)
# TODO Move back to models.WEDNESDAY
def get_next_weekday(allow_today=True, weekday=models.FRIDAY):
    # Get today
    day = get_today()

    # If today is not allowed (today may be FRIDAY and we want to get the
    # next one)
    if not allow_today:
        day += timedelta(days=1)

    # Add as many days as needed to jump to next FRIDAY
    days_till_next_weekday = (weekday - day.weekday()) % 7
    day += timedelta(days=days_till_next_weekday)

    return day

# Calculate the next distribution date


def get_next_distribution_date(allow_today=True):
    candidate_date = get_next_weekday(allow_today)

    # While the calculated date corresponds to a skipped date, get next week
    while models.SkippedDistributionDate.objects.filter(
            skipped_date=candidate_date):
        candidate_date += timedelta(days=7)

    return candidate_date


# Calculate the next distribution date for the given producer
def get_producer_next_distribution_date(producer_id, allow_today=True):
    producer = models.Producer.objects.get(pk=producer_id)
    candidate_date = get_next_weekday(allow_today)

    iterations = 1

    # While the calculated date corresponds to a skipped date,
    # or producer has limited availability and he/she is not available on
    # that date, get next week
    while models.SkippedDistributionDate.objects.filter(
            skipped_date=candidate_date) \
            or (producer.limited_availability and
                not models.ProducerAvailableDate.objects.filter(
                    available_date=candidate_date,
                    producer=producer)):
        candidate_date += timedelta(days=7)

        # If there are no available dates in the next 5 weeks, return a date in
        # the far far future
        if iterations > 5:
            return date(2040, 1, 1)

        iterations += 1

    return candidate_date


# Returns the last date when products were distributed
def get_last_distribution_date():
    last_distributed_product = models.Product.objects.all(
    ).order_by("-distribution_date").first()

    if last_distributed_product:
        return last_distributed_product.distribution_date
    else:
        return None


# Returns the last date when this producer's products were distributed
def get_producer_last_distribution_date(producer_id, allow_today=False):
    if allow_today:
        last_distributed_product = models.Product.objects.filter(
            category__producer_id=producer_id,
            distribution_date__lte=get_today()) \
            .order_by("-distribution_date").first()
    else:
        # Consider only products which were distributed at least 6 days ago
        # These are the ones which are closed for being rated
        distribution_limit = get_today() - timedelta(days=6)

        last_distributed_product = models.Product.objects.filter(
            category__producer_id=producer_id,
            distribution_date__lt=distribution_limit) \
            .order_by("-distribution_date").first()

    if last_distributed_product:
        return last_distributed_product.distribution_date
    else:
        return None


# Returns the order limit date for the given producer and given
# distribution date
def get_producer_order_limit_date(producer, next_dist_date):
    zone = pytztimezone(settings.TIME_ZONE)

    day = next_dist_date
    day = zone.localize(datetime.datetime(day.year, day.month,
                                          day.day, producer.order_hour),
                        is_dst=False)

    days_to_substract = (next_dist_date.weekday() - producer.order_day) % 7
    day -= timedelta(days=days_to_substract)

    # Save the datetime in UTC timezone
    day = day.astimezone(pytztimezone("UTC"))

    return day


def get_today():
    return timezone.now().astimezone(pytztimezone(settings.TIME_ZONE)).date()


def get_now():
    return timezone.now()


def send_email_to_active_users(subject, content):
    # Get list of active members
    active_users = User.objects.filter(
        Q(username__contains='@') & Q(is_active=True))
    bcc_list = []

    for user in active_users:
        # For each member, append the email to the BCC list
        bcc_list.append(user.email)

        # If member has secondary email, add it to BCC list too
        try:
            if user.extrainfo.secondary_email and \
                    len(user.extrainfo.secondary_email) > 0:
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


def send_email_with_cc(subject, content, to, cc):
    text_content = html2text.html2text(content)
    email = EmailMultiAlternatives(subject, text_content, to=to, cc=cc)
    email.attach_alternative(content, "text/html")
    email.send()


def send_email_to_user(subject, content, user):
    to_list = [user.email]
    try:
        if user.extrainfo.secondary_email and \
                len(user.extrainfo.secondary_email) > 0:
            to_list.append(user.extrainfo.secondary_email)
    except ObjectDoesNotExist:
        pass

    text_content = html2text.html2text(content)
    email = EmailMultiAlternatives(subject, text_content, to=to_list)
    email.attach_alternative(content, "text/html")
    return email.send()


def update_distribution_task_information(year):
    update_log = ""

    with transaction.atomic():
        # Directory where to find the private key
        data_dir = os.path.join(settings.BASE_DIR, 'data')

        # Setup the connection to Google Calendar API
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            os.path.join(data_dir, "serviceaccount.json"),
            scopes=['https://www.googleapis.com/auth/sqlservice.admin', 'https://www.googleapis.com/auth/calendar'])

        #client_email = '975533004012-d4veh1666grh6es8bq0celae34u9ag7k@developer.gserviceaccount.com'

        http = Http()
        http = credentials.authorize(http)
        service = build('calendar', 'v3', http=http)

        year_beginning = str(year) + "-01-01T00:00:00Z"
        request = service.events().list(
            calendarId='lt3p1poe2spctu4u9vogokk59g@group.calendar.google.com',
            timeMin=year_beginning)

        # Delete old task objects for the given year
        models.DistributionTask.objects.filter(
            distribution_date__year=year).delete()
        print("Deleted old tasks")

        # Loop until all pages have been processed.
        while request is not None:
            # Get the next page.
            response = request.execute()
            for event in response.get('items', []):
                print("Another event")
                distribution_date = event.get("start", "").get("dateTime", "")

                # Continue with next iteration if dist date not valid
                if distribution_date == "":
                    continue

                distribution_date = parse_date(distribution_date[0:10])
                date_string = distribution_date.strftime('%d/%m/%Y')

                task_members = []

                for attendee in event.get('attendees', []):
                    current_email = attendee.get('email', "")

                    # Continue with next iteration if email not valid (or it is
                    # admin email)
                    if current_email == "" \
                       or current_email == "broquilgotic@gmail.com":
                        continue

                    # Find user for this email
                    user = models.User.objects.filter(
                        email=current_email).first()

                    # If not found, try the secondary email too
                    if not user:
                        extra_info = models.ExtraInfo.objects.filter(
                            secondary_email=current_email).first()

                        if extra_info:
                            user = extra_info.user
                        else:
                            message = _(
                                "Could not find member with email:") + ""
                            update_log = update_log + "<br>" + date_string + \
                                " " + message + " " + current_email
                            continue

                    # If the user is already added to the event, skip
                    if user in task_members:
                        #message = _(
                        #    "Member exists twice in event, email:") + ""
                        #update_log = update_log + "<br>" + date_string + \
                        #    " " + message + " " + current_email
                        continue

                    # Add the user to the event
                    task = models.DistributionTask(
                        distribution_date=distribution_date, user=user)
                    task.save()

                    task_members.append(user)

            # Get the next request object by passing the previous request
            # object to the list_next method.
            request = service.events().list_next(request, response)

    print("Transaction finished successfully")
    return update_log
