# -*- coding: utf-8 -*-
import datetime
from datetime import date

import elbroquil.libraries as libs
import elbroquil.models as models
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import User
from django.db.models import F, Max, Q
from django.shortcuts import render
from django.utils.dateparse import *
from django.views.generic import TemplateView


class ViewDistributionDetailView(LoginRequiredMixin, TemplateView):
    """View distribution details and account summary"""

    template_name = "management/view_distribution_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Form fields
        only_latest_dates = True
        selected_date = None
        date_texts = []
        date_values = []
        detail_records = models.DistributionAccountDetail.objects.all().order_by("-date")

        not_arrived_product_list = []
        amount_changed_product_list = []

        # Account summary values
        expected_initial_cash = 0
        initial_cash = 0
        member_consumed_amount = 0
        debt_balance = 0
        collected_amount = 0
        quarterly_fee_collected_amount = 0
        final_amount = 0
        expected_final_amount = 0
        large_final_difference = False

        producer_payments = []

        # Store latest few dates in variable
        for detail in detail_records:
            if selected_date is None:
                selected_date = detail.date.strftime("%Y-%m-%d")

            date_texts.append(detail.date)
            date_values.append(detail.date.strftime("%Y-%m-%d"))

            # Limit to latest 10 dates
            if only_latest_dates and len(date_texts) >= 10:
                break

        if selected_date is not None and selected_date != "-1":
            # Choose the list of ordered products (total quantity > 0)
            products = models.Product.objects.filter(
                archived=False, distribution_date=selected_date, total_quantity__gt=0
            ).order_by("category__sort_order", "name")

            # Separate the products according to their status
            for product in products:
                if product.total_quantity == product.arrived_quantity:
                    pass  # No incidents
                elif product.arrived_quantity == 0:
                    not_arrived_product_list.append(product)  # Did not arrive
                else:
                    # If product is ordered in units and charged in kg's, it's not an incident
                    if product.unit == "kg" and product.integer_demand:
                        pass
                    else:
                        amount_changed_product_list.append(product)  # Amount changed

            # Load accounting summary information
            record = models.DistributionAccountDetail.objects.filter(date=selected_date).first()

            if record:
                expected_initial_cash = record.expected_initial_amount
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

        distribution_dates = list(zip(date_texts, date_values))

        context.update(
            {
                "selected_date": selected_date,
                "only_latest_dates": only_latest_dates,
                "distribution_dates": distribution_dates,
                "not_arrived_product_list": not_arrived_product_list,
                "amount_changed_product_list": amount_changed_product_list,
                "expected_initial_cash": expected_initial_cash,
                "initial_cash": initial_cash,
                "initial_cash_difference": expected_initial_cash - initial_cash,
                "collected_amount": collected_amount,
                "member_consumed_amount": member_consumed_amount,
                "debt_balance": debt_balance,
                "quarterly_fee_collected_amount": quarterly_fee_collected_amount,
                "final_amount": final_amount,
                "expected_final_amount": expected_final_amount,
                "large_final_difference": large_final_difference,
                "producer_payments": producer_payments,
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        selected_date = request.POST.get("date")
        only_latest_dates = request.POST.get("only-latest") is not None

        # Get updated context with POST data
        context = self.get_context_data()
        # Override with posted values
        context["selected_date"] = selected_date
        context["only_latest_dates"] = only_latest_dates

        # Recalculate based on selected date
        # This logic should be refactored but keeping it simple for now
        return self.render_to_response(context)


class ViewDistributionTaskInformationView(LoginRequiredMixin, TemplateView):
    """View distribution task assignments"""

    template_name = "management/view_distribution_task_information.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        selected_year = libs.get_today().year
        update_log = ""

        context.update(
            {
                "selected_year": selected_year,
                "yearly_tasks": [],
                "member_summary": [],
                "available_years": list(range(2015, (libs.get_today() + datetime.timedelta(60)).year + 1)),
                "update_log": update_log,
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        selected_year = int(request.POST.get("year"))
        form_name = request.POST.get("form-name").strip()
        update_log = ""

        # If "update-form" is submitted, re-read task information from calendar
        if form_name == "update-form":
            update_log = libs.update_distribution_task_information(selected_year)

        # Choose the list of tasks for the selected year
        distribution_tasks = (
            models.DistributionTask.objects.filter(distribution_date__year=selected_year)
            .prefetch_related("user")
            .order_by("distribution_date")
        )

        # Separate the products according to their status
        current_distribution_date = None
        current_task_members = []
        yearly_tasks = []
        member_task_names = []
        member_task_counts = []
        add_month_row = []

        # Prepare the array containing [dist_date, members] pairs
        for task in distribution_tasks:
            member_full_name = task.user.first_name + " " + task.user.last_name

            # If member_full_name exists in member_task_names, update count
            if member_full_name in member_task_names:
                member_index = member_task_names.index(member_full_name)
                member_task_counts[member_index] = member_task_counts[member_index] + 1
            else:
                member_task_names.append(member_full_name)
                member_task_counts.append(1)

            if task.distribution_date != current_distribution_date:
                if current_task_members:
                    yearly_tasks.append([current_distribution_date, current_task_members])

                if (
                    current_distribution_date is None
                    or current_distribution_date.month != task.distribution_date.month
                ):
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
        indexes = list(range(len(member_task_counts)))
        indexes.sort(key=member_task_counts.__getitem__, reverse=True)

        member_task_names2 = list(map(member_task_names.__getitem__, indexes))
        member_task_counts2 = list(map(member_task_counts.__getitem__, indexes))

        member_summary = list(zip(member_task_names2, member_task_counts2))
        yearly_tasks = list(zip(yearly_tasks, add_month_row))

        context = self.get_context_data()
        context.update(
            {
                "selected_year": selected_year,
                "yearly_tasks": yearly_tasks,
                "member_summary": member_summary,
                "update_log": update_log,
            }
        )
        return self.render_to_response(context)


class ViewDebtsView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """View latest debt and payment information for each user"""

    template_name = "fee/view_debts.html"
    permission_required = "elbroquil.accounting"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get all active users
        users = User.objects.filter(Q(username__contains="@") & Q(is_active=True)).order_by("first_name", "last_name")

        # Get the latest debt and payment for each user
        user_debts = []

        for user in users:
            # Get the latest debt for this user
            latest_debt = models.Debt.objects.filter(user=user).order_by("-payment__date").first()

            # Get the latest payment for this user
            latest_payment = models.Payment.objects.filter(user=user).order_by("-date").first()

            user_debts.append(
                {
                    "user": user,
                    "latest_debt": latest_debt,
                    "latest_payment": latest_payment,
                }
            )

        context["user_debts"] = user_debts
        return context


class ViewAccountingDetailView(LoginRequiredMixin, TemplateView):
    """View detailed accounting information"""

    template_name = "management/view_accounting_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # By default, show last two months
        today = libs.get_today()
        start_date = today.strftime("%d/%m/%Y")
        end_date = (today - datetime.timedelta(60)).strftime("%d/%m/%Y")

        context.update(
            {
                "start_date": start_date,
                "end_date": end_date,
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        start_date = request.POST.get("start-date").strip()
        end_date = request.POST.get("end-date").strip()

        context = self.get_context_data()
        context["start_date"] = start_date
        context["end_date"] = end_date

        # TODO: Implement accounting detail logic
        # Fetch records from distr. information and acc. movements
        # Iterate at the same time respecting the chronology
        # Fill a 2D array with the information to display on the page
        #   Date, before, after, comment, before, after, explanation
        return self.render_to_response(context)
