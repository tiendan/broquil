# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from decimal import Decimal

import elbroquil.libraries as libs
import elbroquil.models as models
import project.settings as settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Avg, Q
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView


class OrderHistoryView(LoginRequiredMixin, TemplateView):
    """View order history for a member"""

    template_name = "order/order_history.html"

    def dispatch(self, request, *args, **kwargs):
        # Redirect non-members to order totals page
        if request.user.username.find("@") == -1:
            return HttpResponseRedirect(reverse("view_order_totals"))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Initialize variables
        only_latest_dates = True
        selected_date = None
        date_texts = []
        date_values = []

        # Get payment records
        payment_records = models.Payment.objects.filter(user=self.request.user).order_by("-date")

        # Build list of available dates
        for payment in payment_records:
            payment_date_local = timezone.localtime(payment.date)

            if selected_date is None:
                selected_date = payment_date_local.strftime("%Y-%m-%d")

            date_texts.append(payment_date_local.date())
            date_values.append(payment_date_local.strftime("%Y-%m-%d"))

            if only_latest_dates and len(date_texts) >= 10:
                break

        # Initialize order-related variables
        total_price = 0
        debt_before = 0
        debt_after = 0
        quarterly_fee = 0
        paid_amount = 0
        counted_product_list = []
        not_arrived_product_list = []
        not_ordered_product_list = []
        amount_changed_product_list = []

        if selected_date and selected_date != "-1":
            # Get user orders for the selected date
            user_orders = (
                models.Order.objects.filter(
                    user=self.request.user, archived=False, product__distribution_date=selected_date
                )
                .prefetch_related("product")
                .order_by("product__category__sort_order", "product__pk")
            )

            # Categorize orders by status
            for order in user_orders:
                if order.status == models.STATUS_NORMAL:
                    counted_product_list.append(order)
                    total_price += (order.arrived_quantity * order.product.price).quantize(Decimal(".0001"))

                    if order.arrived_quantity != order.quantity:
                        amount_changed_product_list.append(order)
                elif order.status == models.STATUS_DID_NOT_ARRIVE:
                    not_arrived_product_list.append(order)
                elif order.status == models.STATUS_MIN_ORDER_NOT_MET:
                    not_ordered_product_list.append(order)

            # Get previous debt
            last_debt = (
                models.Debt.objects.filter(user=self.request.user, payment__date__lt=selected_date)
                .order_by("-payment__date")
                .first()
            )

            if last_debt:
                debt_before = last_debt.amount

            # Get payment and related info
            date_start = datetime.strptime(selected_date, "%Y-%m-%d")
            date_end = date_start + timedelta(days=1)
            payment = models.Payment.objects.filter(user=self.request.user, date__range=(date_start, date_end)).first()

            if payment:
                paid_amount = payment.amount

                next_debt = models.Debt.objects.filter(user=self.request.user, payment=payment).first()
                if next_debt:
                    debt_after = next_debt.amount

                quarterly = models.Quarterly.objects.filter(user=self.request.user, payment=payment).first()
                if quarterly:
                    quarterly_fee = quarterly.amount
        else:
            selected_date = 0

        # Ensure order summary is calculated
        if not self.request.session.get("order_total"):
            libs.calculate_order_summary(self.request)

        context.update(
            {
                "orders_with_totals": [],  # Left empty as it's not used
                "total_price": total_price,
                "last_debt": debt_before,
                "next_debt": debt_after,
                "quarterly_fee": quarterly_fee,
                "paid_amount": paid_amount,
                "selected_date": selected_date,
                "only_latest_dates": only_latest_dates,
                "distribution_dates": list(zip(date_texts, date_values)),
                "counted_product_list": counted_product_list,
                "not_arrived_product_list": not_arrived_product_list,
                "not_ordered_product_list": not_ordered_product_list,
                "amount_changed_product_list": amount_changed_product_list,
                "order_total": self.request.session["order_total"],
                "order_summary": self.request.session["order_summary"],
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        # Handle date selection
        context = self.get_context_data()
        selected_date = request.POST.get("date")
        only_latest_dates = request.POST.get("only-latest") is not None

        context["selected_date"] = selected_date
        context["only_latest_dates"] = only_latest_dates

        # Recalculate with selected date
        return self.render_to_response(context)


class UpdateOrderView(LoginRequiredMixin, TemplateView):
    """View to update/place orders for a specific category"""

    template_name = "order/update_order.html"

    def dispatch(self, request, *args, **kwargs):
        # Redirect non-members to order totals page
        if request.user.username.find("@") == -1:
            return HttpResponseRedirect(reverse("view_order_totals"))
        return super().dispatch(request, *args, **kwargs)

    def get_available_categories(self):
        """Get categories with products available for ordering"""
        return (
            models.Category.objects.filter(product__archived=False, product__order_limit_date__gt=libs.get_now())
            .prefetch_related("producer")
            .distinct()
        )

    def get_category_navigation(self, categories, category_no):
        """Calculate previous, current, and next category indices"""
        total_categories = len(categories)

        if category_no == "" and total_categories > 0:
            current = 1
            previous = None
            next_cat = 2 if total_categories > 1 else None
        else:
            current = int(category_no)
            if current > total_categories or current < 1:
                raise Http404

            previous = current - 1 if current > 1 else None
            next_cat = current + 1 if current < total_categories else None

        return previous, current, next_cat

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category_no = kwargs.get("category_no", "")

        categories = self.get_available_categories()
        previous_category, current_category, next_category = self.get_category_navigation(categories, category_no)

        # Get current category and producer
        current_cat_obj = categories[current_category - 1]
        producer = current_cat_obj.producer
        current_category_id = current_cat_obj.pk

        # Get products for current category
        products = models.Product.objects.filter(
            Q(category_id=current_category_id),
            Q(distribution_date__isnull=False),
            Q(order_limit_date__gt=libs.get_now()),
            Q(archived=False),
        ).order_by("id")

        # Get existing user orders
        user_orders = models.Order.objects.filter(
            product__category_id=current_category_id,
            product__distribution_date__isnull=False,
            product__order_limit_date__gt=libs.get_now(),
            archived=False,
            user=self.request.user,
        ).order_by("product__id")

        # Match products with existing orders
        order_index = 0
        product_orders = []
        for i, product in enumerate(products):
            if order_index < len(user_orders) and products[i].id == user_orders[order_index].product.id:
                product_orders.append(user_orders[order_index].quantity)
                order_index += 1
            else:
                product_orders.append(None)

        # Get category names
        category_name = current_cat_obj.visible_name or current_cat_obj.name.title()
        prev_category_name = ""
        next_category_name = ""

        if previous_category:
            prev_cat_obj = categories[previous_category - 1]
            prev_category_name = prev_cat_obj.visible_name or prev_cat_obj.name.title()

        if next_category:
            next_cat_obj = categories[next_category - 1]
            next_category_name = next_cat_obj.visible_name or next_cat_obj.name.title()

        # Calculate progress
        progress = int(100 * current_category / (len(categories) + 1))

        # Ensure order summary is calculated
        if not self.request.session.get("order_total"):
            libs.calculate_order_summary(self.request)

        context.update(
            {
                "products": list(zip(products, product_orders)),
                "producer": producer,
                "category_name": category_name,
                "prev_category_name": prev_category_name,
                "next_category_name": next_category_name,
                "category_no": current_category,
                "prev_category_no": previous_category,
                "next_category_no": next_category,
                "progress": progress,
                "few_hours_later": libs.get_now() + timedelta(hours=4),
                "a_day_later": libs.get_now() + timedelta(days=1),
                "order_total": self.request.session["order_total"],
                "order_summary": self.request.session["order_summary"],
                "category_count": len(categories),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        category_no = kwargs.get("category_no", "")
        categories = self.get_available_categories()
        _, current_category, _ = self.get_category_navigation(categories, category_no)

        current_category_id = categories[current_category - 1].pk

        # Save orders
        with transaction.atomic():
            products = models.Product.objects.filter(
                order_limit_date__gt=libs.get_now(), archived=False, category_id=current_category_id
            )

            # Delete existing orders for this category
            models.Order.objects.filter(
                user=request.user,
                archived=False,
                product__category=current_category_id,
                product__order_limit_date__gt=libs.get_now(),
            ).delete()

            # Create new orders
            for product in products:
                key = f"product_{product.id}"
                item = request.POST.get(key, "").strip()

                if item:
                    models.Order.objects.create(
                        product=product,
                        user=request.user,
                        quantity=Decimal(item.replace(",", ".")),
                        arrived_quantity=Decimal(item.replace(",", ".")),
                    )

        # Recalculate order summary
        libs.calculate_order_summary(request)

        # Re-render the same page with updated data
        return self.get(request, *args, **kwargs)


class ViewOrderView(LoginRequiredMixin, TemplateView):
    """View current orders summary"""

    template_name = "order/view_order.html"

    def dispatch(self, request, *args, **kwargs):
        # Redirect non-members to order totals page
        if request.user.username.find("@") == -1:
            return HttpResponseRedirect(reverse("view_order_totals"))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        today = libs.get_today()
        next_dist_date = libs.get_next_distribution_date()

        # Get all future orders
        all_orders = (
            models.Order.objects.filter(user=self.request.user, archived=False, product__distribution_date__gte=today)
            .prefetch_related("product")
            .order_by("product__category__sort_order", "product__pk")
        )

        # Separate orders by next distribution vs. later
        orders = []
        totals = []
        rest_of_orders = []
        products_sum = 0

        for order in all_orders:
            if order.product.distribution_date != next_dist_date:
                rest_of_orders.append(order)
            else:
                orders.append(order)
                total_price = (order.arrived_quantity * order.product.price).quantize(Decimal(".0001"))
                totals.append(total_price)
                products_sum += total_price

        # Get debt
        debt = 0
        last_debt = (
            models.Debt.objects.filter(user_id=self.request.user, payment__date__lt=today)
            .order_by("-payment__date")
            .first()
        )

        if last_debt:
            debt = last_debt.amount

        # Get quarterly fee
        quarterly_fee = 0
        quarterly = models.Quarterly.objects.filter(
            Q(user=self.request.user),
            Q(created_date__gt=today - timedelta(days=60)),
            Q(payment__isnull=True) | Q(payment__date=today),
        ).first()

        if quarterly:
            quarterly_fee = quarterly.amount

        overall_sum = products_sum + debt + quarterly_fee

        # Get available product count
        available_product_count = models.Product.objects.filter(
            archived=False, order_limit_date__gt=libs.get_now()
        ).count()

        # Calculate order summary
        libs.calculate_order_summary(self.request)

        # Get categories
        categories = models.Category.objects.filter(
            product__archived=False, product__order_limit_date__gt=libs.get_now()
        ).distinct()

        context.update(
            {
                "orders_with_totals": list(zip(orders, totals)),
                "products_sum": products_sum,
                "overall_sum": overall_sum,
                "debt": debt,
                "quarterly_fee": quarterly_fee,
                "available_product_count": available_product_count,
                "rest_of_orders": rest_of_orders,
                "order_total": self.request.session["order_total"],
                "order_summary": self.request.session["order_summary"],
                "category_count": len(categories),
            }
        )
        return context
