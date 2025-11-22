# -*- coding: utf-8 -*-
import ast
import datetime
import logging
import os
from decimal import Decimal

import elbroquil.libraries as libs
import elbroquil.models as models
import elbroquil.parse as parser
import project.settings as settings
import xlrd
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.utils.dateparse import *
from django.utils.encoding import *
from django.views import View
from django.views.generic import FormView, TemplateView
from elbroquil.forms import CheckProductsForm, UploadProductsForm

# Get an instance of a logger
logger = logging.getLogger("MYAPP")


class UploadProductsView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """View to upload Excel files to define products"""

    template_name = "product/upload_products.html"
    form_class = UploadProductsForm
    permission_required = "elbroquil.modify_products"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class CheckProductsView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """View to check the parsed product information from the Excel files"""

    permission_required = "elbroquil.modify_products"

    def post(self, request):
        try:
            products = []
            distribution_date = ""
            order_limit_date = ""
            producer_id = ""
            date_error = False

            # Read posted form
            form = UploadProductsForm(request.POST, request.FILES)

            if form.is_valid():
                # Open Excel workbook and read the related parameters
                # (producer and Excel file format)

                # Directory where to save attachments (default: current)
                detach_dir = os.path.join(settings.BASE_DIR, "data", "temp")

                file_path = os.path.join(detach_dir, "uploaded_products.xls")

                fp = open(file_path, "wb")
                fp.write(form.cleaned_data["excel_file"].read())
                fp.close()

                book = xlrd.open_workbook(file_path)

                producer_id = form.cleaned_data["producer"].id
                excel_format = form.cleaned_data["producer"].excel_format
                logger.error("Check Products")
                logger.error("PRODUCER ID: " + str(producer_id))
                logger.error("EXCEL FORMAT: " + str(excel_format))

                # Choose the appropriate parsing function depending on
                # file format
                if excel_format == models.CAL_ROSSET:
                    products = parser.parse_cal_rosset(book)
                elif excel_format == models.CAN_PIPI:
                    products = parser.parse_can_pipirimosca(book)
                elif excel_format == models.STANDARD:
                    products, distribution_date, order_limit_date = parser.parse_standard(book)

                # If dates are entered, check if there is a problem with it
                # (whether they are past dates)
                if distribution_date != "":
                    distribution_date_parsed = parse_date(distribution_date)
                    order_limit_date_parsed = parse_datetime(order_limit_date)

                    if distribution_date_parsed < libs.get_today() or order_limit_date_parsed < libs.get_now().replace(
                        tzinfo=None
                    ):
                        date_error = True

                return render(
                    request,
                    "product/check_product_info.html",
                    {
                        "products": products,
                        "producer": producer_id,
                        "distribution_date": distribution_date,
                        "order_limit_date": order_limit_date,
                        "date_error": date_error,
                    },
                )
            else:
                # If form not valid, render the form page again
                return render(
                    request,
                    "product/upload_products.html",
                    {
                        "form": form,
                    },
                )
        except ValueError as e:
            form = UploadProductsForm()

            return render(
                request,
                "product/upload_products.html",
                {
                    "form": form,
                    "error_message": e,
                },
            )

    def get(self, request):
        # If nothing is posted, redirect to Excel upload page
        return HttpResponseRedirect(reverse("upload_products"))


class ConfirmProductsView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """After parsed product information is verified, this view adds them to database"""

    permission_required = "elbroquil.modify_products"

    def post(self, request):
        form = CheckProductsForm(request.POST)
        form.is_valid()
        table_data = ast.literal_eval(form.cleaned_data["table_data"])
        producer_id = form.cleaned_data["producer_id"]
        producer = models.Producer.objects.get(id=producer_id)
        distribution_date = None
        order_limit_date = None

        if form.cleaned_data.get("distribution_date"):
            distribution_date = form.cleaned_data["distribution_date"].strip()

        if form.cleaned_data.get("order_limit_date"):
            order_limit_date = form.cleaned_data["order_limit_date"].strip()

        logger.debug("Got dates")
        # If distribution date is passed, parse the strings and create DateTime
        # objects with timezone info
        if distribution_date and order_limit_date:
            distribution_date = parse_date(distribution_date)
            order_limit_date = parse_datetime(order_limit_date)

            # Create timezone-aware datetime using Django's make_aware
            from django.utils import timezone as tz

            order_limit_date = tz.make_aware(
                datetime.datetime(
                    order_limit_date.year, order_limit_date.month, order_limit_date.day, order_limit_date.hour
                )
            )
            order_limit_date = order_limit_date.astimezone(datetime.timezone.utc)
            logger.debug("Order limit date is parsed")

        with transaction.atomic():
            # Delete old products from the same producer
            models.Product.objects.filter(
                distribution_date=distribution_date, category__producer_id=producer_id
            ).delete()
            logger.info("Deleted old products")
            # Insert new products one by one
            for product_info in table_data:
                category_text = product_info[0]
                name_text = force_str(product_info[1])
                price_text = product_info[2].replace(",", ".")
                unit_text = product_info[3]
                origin_text = product_info[4]
                comments_text = product_info[5]

                # Clean the unit text and remove currency char and extra chars
                unit_text = unit_text.replace("€", "").replace("*", "").replace("/", "").strip()

                # If comments include the word unitat, or the unit is not kilos
                #    the demand should be made in units
                integer_demand = "unitat" in comments_text.lower() or unit_text.lower() != "kg"

                for exceptional_product in ["carabassa", "carbassa", "síndria", "meló", "mango"]:
                    integer_demand = integer_demand or exceptional_product in name_text.lower()

                # If there is extra unit demand information, use it to
                # overwrite current info
                if len(product_info) > 6:
                    demand_text = product_info[6].strip() or "NO"

                    integer_demand = demand_text != "NO"

                logger.debug("Prepared product")
                logger.debug(category_text)
                logger.debug(producer_id)
                category, created = models.Category.objects.get_or_create(name=category_text, producer_id=producer_id)

                logger.debug("Got category")
                logger.debug(category)
                logger.debug(price_text)
                logger.debug(distribution_date)

                prod = models.Product(
                    name=name_text,
                    category_id=category.id,
                    origin=origin_text,
                    comments=comments_text,
                    price=Decimal(price_text),
                    unit=unit_text,
                    integer_demand=integer_demand,
                    distribution_date=distribution_date,
                    order_limit_date=order_limit_date,
                )
                prod.save()
                logger.debug("Saved product")

        logger.info("Redirecting to view products")
        return HttpResponseRedirect(reverse("view_products", args=(producer_id,)))

    def get(self, request):
        return HttpResponseRedirect(reverse("upload_products"))


class ViewProductsView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """View to display products for a producer"""

    template_name = "product/view_defined_products.html"
    permission_required = "elbroquil.modify_products"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        producer_id = kwargs.get("producer_id", "")
        products = []

        if producer_id != "":
            products = models.Product.objects.filter(
                distribution_date=None, category__producer_id=int(producer_id)
            ).order_by("category__sort_order", "id")

        producers = models.Producer.objects.all().order_by("company_name")

        # If there are no products with dist_date=None, choose the ones
        # where dist_date > now
        if len(products) == 0 and producer_id != "":
            products = models.Product.objects.filter(
                Q(distribution_date__gt=libs.get_today()), category__producer_id=int(producer_id)
            ).order_by("category__sort_order", "id")

        add_category_row = []
        prev_category = ""

        for prod in products:
            if prod.category.name != prev_category:
                add_category_row.append(True)
                prev_category = prod.category.name
            else:
                add_category_row.append(False)

        if producer_id != "":
            producer_id = int(producer_id)

        context["products"] = list(zip(products, add_category_row))
        context["producers"] = producers
        context["producer_id"] = producer_id
        return context

    def post(self, request, **kwargs):
        producer_id = request.POST["producer_id"]
        return HttpResponseRedirect(reverse("view_products", args=(producer_id,)))
