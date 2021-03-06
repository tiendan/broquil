# -*- coding: utf-8 -*-
from decimal import Decimal
from datetime import datetime, timedelta
from pytz import timezone as pytztimezone

from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Q, Avg
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render

import elbroquil.libraries as libs
import elbroquil.models as models

import project.settings as settings


@login_required
def order_history(request):
    if request.user.username.find("@") == -1:
        return HttpResponseRedirect(reverse('view_order_totals', args=()))

    # Form fields
    only_latest_dates = True
    selected_date = None
    date_texts = []
    date_values = []
    payment_records = models.Payment.objects.filter(user=request.user) \
        .order_by("-date")

    totals = []
    orders = []
    debt_before = 0
    debt_after = 0
    quarterly_fee = 0
    total_price = 0
    paid_amount = 0

    counted_product_list = []
    not_arrived_product_list = []
    not_ordered_product_list = []
    amount_changed_product_list = []

    # Read post variables
    if request.method == 'POST':
        selected_date = request.POST.get("date")
        only_latest_dates = request.POST.get("only-latest") is not None

    # Store latest few dates in variable
    zone = pytztimezone(settings.TIME_ZONE)

    for payment in payment_records:
        if selected_date is None:
            selected_date = zone.normalize(payment.date).strftime("%Y-%m-%d")

        date_texts.append(zone.normalize(payment.date).date)
        date_values.append(zone.normalize(payment.date).strftime("%Y-%m-%d"))

        # Limit to latest 10 dates
        if only_latest_dates and len(date_texts) >= 10:
            break

    if selected_date is not None and selected_date != "-1":
        user_orders = models.Order.objects.filter(
            user=request.user,
            archived=False,
            product__distribution_date=selected_date) \
            .prefetch_related('product') \
            .order_by('product__category__sort_order', 'product__pk')

        # Separate the orders according to their status and calculate the order
        # sum using only the orders which are OK (that arrived)
        for order in user_orders:
            if order.status == models.STATUS_NORMAL:
                counted_product_list.append(order)
                total_price += (order.arrived_quantity * order.product.price) \
                    .quantize(Decimal('.0001'))

                if order.arrived_quantity != order.quantity:
                    amount_changed_product_list.append(order)

                # orders.append(order)
                # totals.append((order.arrived_quantity*order.product.price).quantize(Decimal('.0001'))
            elif order.status == models.STATUS_DID_NOT_ARRIVE:
                not_arrived_product_list.append(order)
            elif order.status == models.STATUS_MIN_ORDER_NOT_MET:
                not_ordered_product_list.append(order)

        # Get debt from last weeks (if exists)
        last_debt = models.Debt.objects.filter(
            user=request.user,
            payment__date__lt=selected_date).order_by('-payment__date').first()

        if last_debt is not None:
            debt_before = last_debt.amount

        # Get the user payment for this distribution date
        date_start = datetime.strptime(selected_date, "%Y-%m-%d")
        date_end = date_start + timedelta(days=1)
        payment = models.Payment.objects.filter(
            user=request.user, date__range=(date_start, date_end)).first()

        if payment is not None:
            paid_amount = payment.amount

            # Get debt saved for next weeks
            next_debt = models.Debt.objects.filter(
                user=request.user, payment=payment).first()

            if next_debt is not None:
                debt_after = next_debt.amount

            # Get paid quarterly fee (if exists)
            quarterly = models.Quarterly.objects.filter(
                user=request.user, payment=payment).first()

            if quarterly is not None:
                quarterly_fee = quarterly.amount
    else:
        selected_date = 0

    orders_with_totals = list(zip(orders, totals))

    if not request.session.get('order_total'):
        libs.calculate_order_summary(request)

    distribution_dates = list(zip(date_texts, date_values))

    return render(request, 'order/order_history.html',
                  {
                      'orders_with_totals': orders_with_totals,
                      'total_price': total_price,
                      'last_debt': debt_before,
                      'next_debt': debt_after,
                      'quarterly_fee': quarterly_fee,
                      'paid_amount': paid_amount,

                      'selected_date': selected_date,
                      'only_latest_dates': only_latest_dates,
                      'distribution_dates': distribution_dates,

                      'counted_product_list': counted_product_list,
                      'not_arrived_product_list': not_arrived_product_list,
                      'not_ordered_product_list': not_ordered_product_list,
                      'amount_changed_product_list': amount_changed_product_list,

                      'order_total': request.session['order_total'],
                      'order_summary': request.session['order_summary'],
                  })


# Page to enable users update/place their orders
@login_required
def update_order(request, category_no=''):
    if request.user.username.find("@") == -1:
        return HttpResponseRedirect(reverse('view_order_totals', args=()))
    # Choose the available categories:
    #    - having products with order limit date in the future
    #    - not archived
    categories = models.Category.objects.filter(
        product__archived=False,
        product__order_limit_date__gt=libs.get_now()) \
        .prefetch_related('producer').distinct()

    # Choose the indices for the current, previous and next categories
    previous_category = None
    current_category = None
    next_category = None
    current_category_id = None

    # If no category chosen, choose the first as default and second as next
    if category_no == '' and len(categories) > 0:
        current_category = 1
        if len(categories) > 1:
            next_category = 2
    else:
        # If given category no is outside bounds, give 404
        current_category = int(category_no)
        if current_category > len(categories) or current_category < 1:
            raise Http404

        if current_category > 1:
            previous_category = current_category - 1

        if current_category < len(categories):
            next_category = current_category + 1

    producer = categories[current_category - 1].producer

    # Get current category id
    current_category_id = categories[current_category - 1].pk

    if request.method == 'POST':  # If the form has been submitted...
        # Delete old orders and insert new ones
        with transaction.atomic():
            products = models.Product.objects.filter(
                order_limit_date__gt=libs.get_now(),
                archived=False,
                category_id=current_category_id)

            models.Order.objects.filter(
                user=request.user,
                archived=False,
                product__category=current_category_id,
                product__order_limit_date__gt=libs.get_now()).delete()

            for p in products:
                key = "product_" + str(p.id)
                item = request.POST.get(key).strip()
                if len(item) > 0:
                    order = models.Order()
                    order.product = p
                    order.user = request.user
                    order.quantity = Decimal(item.replace(',', '.'))
                    order.arrived_quantity = order.quantity
                    order.save()

        # Recalculate the order summary
        libs.calculate_order_summary(request)

    products = models.Product.objects.filter(
        Q(category_id=current_category_id),
        Q(distribution_date__isnull=False),
        Q(order_limit_date__gt=libs.get_now()),
        Q(archived=False)).order_by('id')

    user_orders = models.Order.objects.filter(
        product__category_id=current_category_id,
        product__distribution_date__isnull=False,
        product__order_limit_date__gt=libs.get_now(),
        archived=False,
        user=request.user).order_by('product__id')

    order_index = 0
    product_orders = []
    for i in range(0, len(products)):
        if order_index < len(user_orders) \
           and products[i].id == user_orders[order_index].product.id:
            product_orders.append(user_orders[order_index].quantity)
            order_index += 1
        else:
            product_orders.append(None)

    prev_category_name = ''
    category_name = categories[current_category - 1].visible_name \
        or categories[current_category - 1].name.title()
    next_category_name = ''

    if previous_category:
        prev_category_name = categories[previous_category - 1].visible_name \
            or categories[previous_category - 1].name.title()

    if next_category:
        next_category_name = categories[next_category - 1].visible_name \
            or categories[next_category - 1].name.title()

    products = list(zip(products, product_orders))

    progress = int(100 * current_category / (len(categories) + 1))

    if not request.session.get('order_total'):
        libs.calculate_order_summary(request)

    few_hours_later = libs.get_now() + timedelta(hours=4)
    a_day_later = libs.get_now() + timedelta(days=1)

    return render(request, 'order/update_order.html',
                  {
                      'products': products,
                      'producer': producer,

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

                      'category_count': len(categories),
                  })


@login_required
def view_order(request):
    if request.user.username.find("@") == -1:
        return HttpResponseRedirect(reverse('view_order_totals', args=()))

    today = libs.get_today()
    all_orders = models.Order.objects.filter(
        user=request.user,
        archived=False,
        product__distribution_date__gte=today) \
        .prefetch_related('product') \
        .order_by('product__category__sort_order', 'product__pk')

    next_dist_date = libs.get_next_distribution_date()
    totals = []
    orders = []
    rest_of_orders = []
    debt = 0
    quarterly_fee = 0
    products_sum = 0
    overall_sum = 0

    for order in all_orders:
        if order.product.distribution_date != next_dist_date:
            rest_of_orders.append(order)
        else:
            orders.append(order)
            total_price = (order.arrived_quantity * order.product.price) \
                .quantize(Decimal('.0001'))
            totals.append(total_price)
            products_sum += total_price

    available_product_count = models.Product.objects.filter(
        archived=False,
        order_limit_date__gt=libs.get_now()).count()

    orders_with_totals = list(zip(orders, totals))

    # Get debt from last weeks (if exists)
    last_debt = models.Debt.objects.filter(
        user_id=request.user,
        payment__date__lt=today).order_by('-payment__date').first()

    if last_debt is not None:
        debt = last_debt.amount

    quarterly = models.Quarterly.objects.filter(
        Q(user=request.user),
        Q(created_date__gt=today - timedelta(days=60)),
        Q(payment__isnull=True) | Q(payment__date=today)).first()

    if quarterly is not None:
        quarterly_fee = quarterly.amount

    overall_sum = products_sum + debt + quarterly_fee

    # Calculate order summary every time this page is shown
    # if not request.session.get('order_total'):
    libs.calculate_order_summary(request)

    categories = models.Category.objects.filter(
        product__archived=False,
        product__order_limit_date__gt=libs.get_now()).distinct()

    return render(request, 'order/view_order.html',
                  {
                      'orders_with_totals': orders_with_totals,
                      'products_sum': products_sum,
                      'overall_sum': overall_sum,
                      'debt': debt,
                      'quarterly_fee': quarterly_fee,
                      'available_product_count': available_product_count,
                      'rest_of_orders': rest_of_orders,

                      'order_total': request.session['order_total'],
                      'order_summary': request.session['order_summary'],

                      'category_count': len(categories),
                  })


@login_required
def rate_products(request):
    # Only rate products that were distributed in the last 5 days
    today = libs.get_today()
    limit_date = today - timedelta(days=5)

    orders = models.Order.objects.filter(
        user=request.user,
        archived=False,
        status=models.STATUS_NORMAL,
        product__distribution_date__gte=limit_date,
        product__distribution_date__lte=today) \
        .prefetch_related('product') \
        .order_by('product__category__sort_order', 'product__name')

    if request.method == 'POST':  # If the form has been submitted...
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
            order.product.average_rating = models.Order.objects.filter(
                product=order.product,
                archived=False,
                status=models.STATUS_NORMAL,
                rating__isnull=False) \
                .aggregate(Avg('rating'))['rating__avg'] or 0

            order.product.save()

            # Update the average rating for the same product that has a
            # distribution date in the future (next week's product) (if exists)
            models.Product.objects.filter(
                distribution_date__gt=libs.get_now(),
                name=order.product.name,
                origin=order.product.origin) \
                .update(average_rating=order.product.average_rating)
            # No need to reload results as we overwrite the only changed column

    if not request.session.get('order_total'):
        libs.calculate_order_summary(request)

    return render(request, 'order/rate_products.html',
                  {
                      'orders': orders,

                      'order_total': request.session['order_total'],
                      'order_summary': request.session['order_summary'],
                  })
