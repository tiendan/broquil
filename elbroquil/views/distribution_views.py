# -*- coding: utf-8 -*-
import logging
from datetime import timedelta
from decimal import Decimal

import elbroquil.libraries as libs
import elbroquil.models as models
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q, Sum
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone

# Set up logger
logger = logging.getLogger(__name__)


@login_required
@permission_required("elbroquil.prepare_baskets")
def view_order_totals(request):
    distribution_date = libs.get_next_distribution_date()
    edit_enabled = distribution_date == libs.get_today()

    # 01 March 2015: Do not show stock products in the first page
    products = models.Product.objects.filter(
        archived=False, distribution_date=distribution_date, total_quantity__gt=0, stock_product=False
    ).order_by("category__sort_order", "id")

    add_category_row = []
    prev_category = ""

    # If the form was submitted
    if request.method == "POST":
        with transaction.atomic():
            for product in products:
                key = "product_arrived_" + str(product.id)
                item = request.POST.get(key).strip()

                if len(item) > 0:
                    # If an amount is entered (or already present) update the
                    # arrived quantity
                    product.arrived_quantity = Decimal(item.replace(",", "."))
                    product.save()
                else:
                    # Else, update the arrived quantity to the original total
                    # quantity
                    product.arrived_quantity = product.total_quantity
                    product.save()

                # Depending on the arrived quantity, set the product orders
                # status
                if product.arrived_quantity == 0:
                    models.Order.objects.filter(product_id=product.id).update(status=models.STATUS_DID_NOT_ARRIVE)
                else:
                    models.Order.objects.filter(product_id=product.id).update(status=models.STATUS_NORMAL)

    for prod in products:
        if prod.category.name != prev_category:
            add_category_row.append(True)
            prev_category = prod.category.name
        else:
            add_category_row.append(False)

    products = list(zip(products, add_category_row))
    return render(
        request,
        "distribution/view_order_totals.html",
        {"products": products, "show_product_links": True, "edit_enabled": edit_enabled},
    )


def get_expected_initial_cash(today):
    # Get the final amount from the previous distribution day
    expected_initial_cash = 0
    previous_account_detail = models.DistributionAccountDetail.objects.filter(date__lt=today).order_by("-date").first()

    if previous_account_detail:
        expected_initial_cash = previous_account_detail.final_amount

    return expected_initial_cash


@login_required
@permission_required("elbroquil.prepare_baskets")
def count_initial_cash(request):
    initial_cash = 0
    today = libs.get_today()

    if request.method == "POST":
        initial_cash = Decimal(request.POST.get("initial-cash").strip())

        account_detail = models.DistributionAccountDetail.objects.filter(date__gte=today).first()

        # If there is no previously saved record for today,
        # create one
        if not account_detail:
            account_detail = models.DistributionAccountDetail()

        # Insert or update the initial amount
        account_detail.initial_amount = initial_cash
        account_detail.save()
    else:
        account_detail = models.DistributionAccountDetail.objects.filter(date__gte=today).first()

        if account_detail:
            initial_cash = account_detail.initial_amount

    previous_final_cash = get_expected_initial_cash(today)

    return render(
        request,
        "distribution/count_initial_cash.html",
        {
            "initial_cash": initial_cash,
            "previous_final_cash": previous_final_cash,
        },
    )


@login_required
@permission_required("elbroquil.prepare_baskets")
def view_basket_counts(request):
    # If basket counts are not already calculated and stored in session,
    # calculate them
    orders = (
        models.Order.objects.filter(product__distribution_date=libs.get_today(), status=models.STATUS_NORMAL)
        .prefetch_related("product", "user")
        .order_by("user__first_name", "user__last_name")
    )

    order_summary = []
    last_order_total = 0
    last_order_user = -1
    last_order_user_name = ""

    for order in orders:
        if order.user.id != last_order_user:
            if last_order_total > 0:
                if last_order_total < 40:
                    order_summary.append([last_order_user, last_order_user_name, last_order_total, 1])
                else:
                    order_summary.append([last_order_user, last_order_user_name, last_order_total, 2])

            last_order_total = 0
            last_order_user = order.user.id
            last_order_user_name = order.user.get_full_name()

        last_order_total += order.arrived_quantity * order.product.price

    if last_order_total > 0:
        if last_order_total < 40:
            order_summary.append([last_order_user, last_order_user_name, last_order_total, 1])
        else:
            order_summary.append([last_order_user, last_order_user_name, last_order_total, 2])

    return render(
        request,
        "distribution/view_basket_counts.html",
        {
            "order_summary": order_summary,
            "product_name": "",
            "prev_product_name": "",
            "next_product_name": "Next prod",
            "current_product_no": 0,
            "prev_product_no": 0,
            "next_product_no": 1,
        },
    )


@login_required
@permission_required("elbroquil.prepare_baskets")
def view_product_orders(request, product_no=""):
    products = models.Product.objects.filter(
        Q(archived=False), Q(distribution_date=libs.get_today()), Q(arrived_quantity__gt=0) | Q(stock_product=True)
    ).order_by("stock_product", "category__sort_order", "id")

    previous_product = None
    current_product_no = None
    next_product = None
    current_product = None
    update_weights = False

    log_messages = ""

    # If no product chosen, choose the first as default and second as next
    if product_no == "" and len(products) > 0:
        current_product_no = 1
        if len(products) > 1:
            next_product = 2
    else:
        current_product_no = int(product_no)

        if current_product_no > 1:
            previous_product = current_product_no - 1

        if current_product_no < len(products):
            next_product = current_product_no + 1

    if current_product_no is None:
        raise Http404

    # Instead of storing current product properties one by one, just store the
    # product object and pass it to the templates
    current_product = products[current_product_no - 1]

    if request.method == "POST":  # If the form has been submitted...
        with transaction.atomic():
            # Update the orders with the new quantities
            orders = models.Order.objects.filter(product_id=current_product.id)

            # Keep track of users who have orders for this product
            users_with_orders = set()

            for o in orders:
                users_with_orders.add(o.user_id)
                key = "order_arrived_" + str(o.id)
                item = request.POST.get(key).strip()

                if len(item) > 0:
                    # Update the arrived quantity and status
                    o.arrived_quantity = Decimal(item.replace(",", "."))

                    if o.arrived_quantity == 0:
                        o.status = models.STATUS_DID_NOT_ARRIVE
                    else:
                        o.status = models.STATUS_NORMAL

                    o.save()

            # If some new orders are added (for members who had not ordered
            # this product originally) create new Order objects so that it is
            # reflected in the final price
            additional_members = request.POST.getlist("additional_member[]")
            additional_quantities = request.POST.getlist("additional_quantity[]")

            for member_id, member_quantity in zip(additional_members, additional_quantities):
                member_quantity = member_quantity.strip()

                if member_id != "" and member_quantity != "" and Decimal(member_quantity) > 0:
                    models.Order.objects.filter(user_id=member_id, product_id=current_product.id).delete()

                    new_order = models.Order(
                        product_id=current_product.id,
                        user_id=member_id,
                        quantity=0,
                        arrived_quantity=Decimal(member_quantity),
                    )

                    new_order.save()
                    users_with_orders.add(int(member_id))

            # Update payments for users who have already paid today
            today = libs.get_today()

            for user_id in users_with_orders:
                # Check if user has already paid today
                existing_payment = models.Payment.objects.filter(user_id=user_id, date__gte=today).first()

                if existing_payment is not None:
                    # Update payment and debt records
                    try:
                        update_member_payment(user_id, today)
                    except Exception as e:
                        logger.error(f"Error updating payment for user {user_id}: {str(e)}")
                        # Re-raise the exception to trigger transaction rollback if needed
                        raise e

    product_orders = models.Order.objects.filter(product__id=current_product.id).order_by(
        "user__first_name", "user__last_name"
    )

    all_members = User.objects.filter(username__contains="@", is_active=True).order_by("first_name", "last_name")

    total_quantity = 0
    total_arrived_quantity = 0

    for i in range(0, len(product_orders)):
        total_quantity = total_quantity + product_orders[i].quantity
        total_arrived_quantity += product_orders[i].arrived_quantity

    prev_product_name = ""
    next_product_name = ""

    if previous_product:
        prev_product_name = products[previous_product - 1].name

    if next_product:
        next_product_name = products[next_product - 1].name

    # If product was marked for "integer demand" but is sold in kg's, need to
    # update its weight
    update_weights = current_product.integer_demand and current_product.unit.lower() == "kg"

    return render(
        request,
        "distribution/view_product_orders.html",
        {
            "all_products": products,
            "product_orders": product_orders,
            "current_product": current_product,
            "prev_product_name": prev_product_name,
            "next_product_name": next_product_name,
            "current_product_no": current_product_no,
            "prev_product_no": previous_product,
            "next_product_no": next_product,
            "total_quantity": total_quantity,
            "total_arrived_quantity": total_arrived_quantity,
            "update_weights": update_weights,
            "total_products": len(products),
            "all_members": all_members,
            "log_messages": log_messages,
        },
    )


@login_required
@permission_required("elbroquil.prepare_baskets")
def view_product_orders_with_id(request, product_id):
    products = models.Product.objects.filter(
        Q(archived=False), Q(distribution_date=libs.get_today()), Q(arrived_quantity__gt=0) | Q(stock_product=True)
    ).order_by("stock_product", "category__sort_order", "id")

    for idx, product in enumerate(products):
        if product.pk == int(product_id):
            return HttpResponseRedirect(reverse("view_product_orders", args=(idx + 1,)))

    raise Http404


@login_required
@permission_required("elbroquil.prepare_baskets")
def member_payment(request):
    member_orders = (
        models.User.objects.filter(order__product__distribution_date=libs.get_today())
        .distinct()
        .order_by("first_name", "last_name")
    )

    member_id = -1

    products = models.Product.objects.filter(
        archived=False, distribution_date=libs.get_today(), arrived_quantity__gt=0
    ).order_by("category__sort_order", "id")

    previous_product = len(products)
    prev_product_name = products.last().name

    today = libs.get_today()
    member_phone = None
    posted_quarterly_fee_paid = None

    if request.method == "POST":
        form_name = request.POST.get("form-name").strip()
        member_id = int(request.POST.get("member-id").strip())

        user = get_object_or_404(User, id=member_id)

        try:
            if user.extrainfo and user.extrainfo.phone:
                member_phone = user.extrainfo.phone

                if user.extrainfo.secondary_phone:
                    member_phone = member_phone + " / " + user.extrainfo.secondary_phone
        except:
            pass

        # If payment form was submitted
        if form_name == "payment-form":
            paid_amount = request.POST.get("amount-paid").strip().replace(",", ".")
            posted_quarterly_fee_paid = request.POST.get("pay-quarterly") is not None

            # Use the update_member_payment function to handle all payment logic
            payment_data = update_member_payment(
                user_id=member_id,
                today=today,
                paid_amount=paid_amount,
                posted_quarterly_fee_paid=posted_quarterly_fee_paid,
            )
        else:
            # Just get the payment data without updating
            payment_data = update_member_payment(user_id=member_id, today=today)
    else:
        # Initialize with empty data
        payment_data = {
            "counted_product_list": [],
            "not_arrived_product_list": [],
            "not_ordered_product_list": [],
            "amount_changed_product_list": [],
            "total_price": Decimal(0),
            "last_debt": Decimal(0),
            "quarterly_fee": Decimal(0),
            "quarterly_fee_paid": False,
            "total_to_pay": Decimal(0),
            "paid_amount": Decimal(0),
            "next_debt": Decimal(0),
            "has_dairy_products": False,
        }

    # June 2015: Do not show + for members who have a payment of 0 euros
    member_payments = (
        models.Payment.objects.filter(date__gte=libs.get_today(), amount__gt=0)
        .prefetch_related("user")
        .order_by("user__first_name", "user__last_name")
    )

    member_payment_index = 0
    member_payment_status = []

    for i in range(0, len(member_orders)):
        if (
            member_payment_index < len(member_payments)
            and member_payments[member_payment_index].user.pk == member_orders[i].pk
        ):
            member_payment_status.append(True)
            member_payment_index = member_payment_index + 1
        else:
            member_payment_status.append(False)

    member_orders = list(zip(member_orders, member_payment_status))

    payment_count = models.Payment.objects.filter(date__gte=today, amount__gt=0).count()

    return render(
        request,
        "distribution/member_payment.html",
        {
            "member_orders": member_orders,
            "paid_count": payment_count,
            "total_count": len(member_orders),
            "member_id": member_id,
            "previous_product": previous_product,
            "prev_product_name": prev_product_name,
            "member_phone": member_phone,
            **payment_data,  # Unpack all payment data
        },
    )


@login_required
@permission_required("elbroquil.prepare_baskets")
def account_summary(request):
    today = libs.get_today()
    expected_initial_cash = get_expected_initial_cash(today)
    initial_cash = 0
    collected_amount = 0
    debt_balance = 0
    final_amount = 0
    expected_final_amount = 0
    notes = ""

    # If form was posted, check if there are any members that have not paid yet
    if request.method == "POST":
        members_with_order = models.User.objects.filter(order__product__distribution_date=libs.get_today()).distinct()

        for member in members_with_order:
            # If there is no payment for this member, calculate the debt and
            # save it for next week
            if models.Payment.objects.filter(date__gte=today, user=member).count() == 0:
                # Get debt from last weeks
                member_debt_amount = 0
                member_debt_from_last_weeks = (
                    models.Debt.objects.filter(user=member, payment__date__lt=today).order_by("-payment__date").first()
                )

                if member_debt_from_last_weeks:
                    member_debt_amount = member_debt_from_last_weeks.amount

                # Calculate order total for this week
                member_total_order = 0
                member_orders = models.Order.objects.filter(
                    user=member, archived=False, product__distribution_date=today, status=models.STATUS_NORMAL
                ).prefetch_related("product")

                for order in member_orders:
                    member_total_order += (order.arrived_quantity * order.product.price).quantize(Decimal(".0001"))

                member_next_debt = member_total_order + member_debt_amount

                # Create a dummy payment object for today (with 0 euros paid)
                payment = models.Payment()
                payment.user = member
                payment.date = libs.get_now()
                payment.amount = 0
                payment.save()

                # Create the debt for the following weeks
                next_debt_object, _ = models.Debt.objects.get_or_create(user=member, payment=payment)

                next_debt_object.amount = member_next_debt
                next_debt_object.save()

                # Create the consumption record for the user
                consumption, _ = models.Consumption.objects.get_or_create(user=member, payment=payment)

                consumption.amount = member_total_order
                consumption.save()

    # Calculate collected amount from Payment table
    collected_amount = models.Payment.objects.filter(date__gte=today).aggregate(Sum("amount"))["amount__sum"] or 0
    member_consumed_amount = (
        models.Consumption.objects.filter(payment__date__gte=today).aggregate(Sum("amount"))["amount__sum"] or 0
    )
    quarterly_fee_collected_amount = (
        models.Quarterly.objects.filter(payment__date__gte=today).aggregate(Sum("amount"))["amount__sum"] or 0
    )

    # Calculate debt balance from Debt table (for each user, check for debt
    # before today and debt today)
    previous_debt_total = 0
    current_debt_total = 0

    all_users = User.objects.filter(username__contains="@")
    for user in all_users:
        # Get today's debt for this user
        debt = models.Debt.objects.filter(user=user, payment__date__gte=today).first()

        # If there is a debt, find the previous debt too and add them to
        # the totals
        if debt:
            current_debt_total += debt.amount

            prev_debt = (
                models.Debt.objects.filter(user=user, payment__date__lt=today).order_by("-payment__date").first()
            )

            if prev_debt:
                previous_debt_total += prev_debt.amount

        # Else if there is no debt from today, find the last debt for the user
        # and add it to both amounts so that it is reflected in the totals
        else:
            prev_debt = (
                models.Debt.objects.filter(user=user, payment__date__lt=today).order_by("-payment__date").first()
            )

            if prev_debt:
                previous_debt_total += prev_debt.amount
                current_debt_total += prev_debt.amount

    # Debt balance is: the net debt change of the users (the extra amount that
    # the cooperative should receive later on)
    debt_balance = current_debt_total - previous_debt_total

    # Read final amount from DistributionAccountDetail table (if record exists
    # for today)
    account_detail = models.DistributionAccountDetail.objects.filter(date__gte=today).first()

    if account_detail:
        initial_cash = account_detail.initial_amount
        final_amount = account_detail.final_amount
        notes = account_detail.notes

    # Calculate producer-required payment amount pairs
    producers_with_order = []
    producer_totals = []
    overall_producer_payment = 0

    all_producers = models.Producer.objects.all().order_by("company_name")
    for producer in all_producers:
        # 01 March 2015: Do not include stock products in the producer payments
        products = models.Product.objects.filter(
            category__producer=producer, distribution_date=today, total_quantity__gt=0, stock_product=False
        )

        producer_sum = 0

        for product in products:
            producer_sum += product.arrived_quantity * product.price

        if producer_sum > 0:
            producer_sum += producer.transportation_cost
            producers_with_order.append(producer)
            producer_totals.append(producer_sum)
            overall_producer_payment += producer_sum

    producer_payments = list(zip(producers_with_order, producer_totals))

    expected_final_amount = (initial_cash + collected_amount - overall_producer_payment).quantize(Decimal(".01"))

    # Get the number of people who made an order and the number of people who
    # paid until now
    order_count = models.User.objects.filter(order__product__distribution_date=today).distinct().count()

    payment_count = models.Payment.objects.filter(date__gte=today).count()

    # If form was posted (final amount updated)
    if request.method == "POST":
        # Get posted final amount
        final_amount = Decimal(request.POST.get("final-amount").strip())
        notes = request.POST.get("notes").strip()

        # Write the calculated values and create/update the DB record
        if not account_detail:
            account_detail = models.DistributionAccountDetail()

        account_detail.expected_initial_amount = expected_initial_cash
        account_detail.member_consumed_amount = member_consumed_amount
        account_detail.total_member_payment_amount = collected_amount
        # account_detail.producer_paid_amount = overall_producer_payment
        account_detail.debt_balance_amount = debt_balance
        account_detail.quarterly_fee_collected_amount = quarterly_fee_collected_amount
        account_detail.expected_final_amount = expected_final_amount

        account_detail.final_amount = final_amount
        account_detail.notes = notes

        account_detail.save()

        # Delete old Producer Payment records and insert new ones
        models.ProducerPayment.objects.filter(date=today).delete()
        for producer, total in producer_payments:
            payment = models.ProducerPayment()
            payment.date = today
            payment.producer = producer
            payment.amount = total
            payment.save()

    return render(
        request,
        "distribution/account_summary.html",
        {
            "expected_initial_amount": expected_initial_cash,
            "initial_amount": initial_cash,
            "initial_amount_difference": expected_initial_cash - initial_cash,
            "collected_amount": collected_amount,
            "debt_balance": debt_balance,
            "producer_payments": producer_payments,
            "final_amount": final_amount,
            "expected_final_amount": expected_final_amount,
            "order_count": order_count,
            "payment_count": payment_count,
            "notes": notes,
            # 'progress': progress
        },
    )


def update_member_payment(user_id, today, paid_amount=None, posted_quarterly_fee_paid=None):
    """
    Update payment and debt records for a member based on their current orders.
    This function recalculates the total price, debt, and updates the payment record.

    Args:
        user_id: The ID of the user whose payment needs to be updated
        today: The date of the current distribution
        paid_amount: Optional amount paid by the user (if None, uses existing payment amount)
        posted_quarterly_fee_paid: Optional flag indicating if quarterly fee was paid

    Returns:
        dict: A dictionary containing all the necessary variables for the template
    """

    # Get all orders for this member
    orders = (
        models.Order.objects.filter(user_id=user_id, archived=False, product__distribution_date=today)
        .prefetch_related("product")
        .order_by("product__category__sort_order", "product__id")
    )

    # Separate the orders according to their status and calculate the order
    # sum using only the orders which are OK (that arrived)
    counted_product_list = []
    not_arrived_product_list = []
    not_ordered_product_list = []
    amount_changed_product_list = []

    total_price = Decimal(0)
    has_dairy_products = False

    for order in orders:
        # If the member has a product from La Selvatana (category_id=13),
        # show the cow! TODO Remove hardcoded ID
        has_dairy_products = has_dairy_products or order.product.category_id == 13

        if order.status == models.STATUS_NORMAL:
            counted_product_list.append(order)

            order_price = (order.arrived_quantity * order.product.price).quantize(Decimal(".0001"))
            total_price += order_price

            if order.arrived_quantity != order.quantity:
                amount_changed_product_list.append(order)

        elif order.status == models.STATUS_DID_NOT_ARRIVE:
            not_arrived_product_list.append(order)
        elif order.status == models.STATUS_MIN_ORDER_NOT_MET:
            not_ordered_product_list.append(order)

    # Round to 2 decimals
    total_price = total_price.quantize(Decimal("0.01"))

    # Get debt from last weeks (if exists)
    last_debt = Decimal(0)
    debt = models.Debt.objects.filter(user_id=user_id, payment__date__lt=today).order_by("-payment__date").first()

    if debt is not None:
        last_debt = debt.amount

    # Check for quarterly fee
    quarterly_fee = Decimal(0)
    quarterly_fee_paid = False
    quarterly = models.Quarterly.objects.filter(
        Q(user_id=user_id),
        Q(created_date__gt=timezone.now() - timedelta(days=60)),
        Q(payment__isnull=True) | Q(payment__date__gte=today),
    ).first()

    if quarterly is not None:
        quarterly_fee = quarterly.amount
        quarterly_fee_paid = quarterly.payment_id is not None

    # Calculate total to pay
    total_to_pay = total_price + last_debt
    if quarterly_fee_paid:
        total_to_pay += quarterly_fee

    # Get existing payment if any
    payment = models.Payment.objects.filter(user_id=user_id, date__gte=today).first()

    # If paid_amount is provided, use it; otherwise use existing payment amount
    if paid_amount is not None:
        paid_amount = Decimal(paid_amount)
    else:
        paid_amount = Decimal(0)
        if payment is not None:
            paid_amount = payment.amount

    # If posted_quarterly_fee_paid is provided, use it to update total_to_pay
    if posted_quarterly_fee_paid is not None:
        quarterly_fee_paid = posted_quarterly_fee_paid
        total_to_pay = total_price + last_debt
        if posted_quarterly_fee_paid:
            total_to_pay += quarterly_fee

    # Calculate next debt
    next_debt = total_to_pay - paid_amount

    # Update payment record
    if payment is not None:
        payment.amount = paid_amount
        payment.save()
    else:
        payment = models.Payment()
        payment.user_id = user_id
        payment.date = libs.get_now()
        payment.amount = paid_amount
        payment.save()

    # Create or update the debt for the following weeks
    next_debt_object, created = models.Debt.objects.get_or_create(user_id=user_id, payment=payment)

    next_debt_object.amount = next_debt
    next_debt_object.save()

    # If there was a quarterly fee, update its row
    if quarterly is not None and posted_quarterly_fee_paid is not None:
        if posted_quarterly_fee_paid:
            quarterly.payment = payment
            quarterly.save()
        else:
            quarterly.payment = None
            quarterly.save()

    # Update Consumption table
    consumption, created = models.Consumption.objects.get_or_create(user_id=user_id, payment=payment)

    consumption.amount = total_price
    consumption.save()

    # Return all necessary variables for the template
    return {
        "counted_product_list": counted_product_list,
        "not_arrived_product_list": not_arrived_product_list,
        "not_ordered_product_list": not_ordered_product_list,
        "amount_changed_product_list": amount_changed_product_list,
        "total_price": total_price,
        "last_debt": last_debt,
        "quarterly_fee": quarterly_fee,
        "quarterly_fee_paid": quarterly_fee_paid,
        "total_to_pay": total_to_pay,
        "paid_amount": paid_amount,
        "next_debt": next_debt,
        "has_dairy_products": has_dairy_products,
        "payment": payment,
        "next_debt_object": next_debt_object,
        "consumption": consumption,
    }
