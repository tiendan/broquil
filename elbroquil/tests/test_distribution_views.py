import datetime
from decimal import Decimal

import elbroquil.libraries as libs
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from elbroquil.models import (
    Category,
    Debt,
    DistributionAccountDetail,
    DistributionDate,
    Order,
    Payment,
    Producer,
    Product,
    Quarterly,
)


class DistributionViewsTest(TestCase):
    def setUp(self):
        # Create a user with necessary permissions
        self.user = User.objects.create_user(
            username="testuser", password="password", first_name="Test", last_name="User"
        )
        content_type = ContentType.objects.get_for_model(Order)
        permission = Permission.objects.create(
            codename="prepare_baskets",
            name="Can prepare baskets",
            content_type=content_type,
        )
        self.user.user_permissions.add(permission)
        self.client.login(username="testuser", password="password")

        # Create producer and category
        self.producer = Producer.objects.create(
            company_name="Test Producer", email="producer@example.com", order_hour=12
        )
        self.category = Category.objects.create(name="Test Category", producer=self.producer)

        # Set up dates
        self.today = libs.get_today()
        self.next_dist_date = libs.get_next_distribution_date()

        # Create DistributionDate if it doesn't exist (some libs functions might rely on it)
        DistributionDate.objects.get_or_create(distribution_date=self.next_dist_date, canceled=False)

        # Create a product for the next distribution date
        self.product = Product.objects.create(
            name="Test Product",
            category=self.category,
            price=Decimal("10.00"),
            unit="kg",
            distribution_date=self.next_dist_date,
            order_limit_date=timezone.now() + datetime.timedelta(days=1),
            total_quantity=Decimal("10.00"),
            arrived_quantity=Decimal("10.00"),
        )

        # Create an order
        self.order = Order.objects.create(
            user=self.user,
            product=self.product,
            quantity=Decimal("2.00"),
            arrived_quantity=Decimal("2.00"),
            status=0,  # STATUS_NORMAL
        )

    def test_view_order_totals_get(self):
        response = self.client.get(reverse("view_order_totals"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "distribution/view_order_totals.html")
        self.assertContains(response, "Test Product")

    def test_view_order_totals_post(self):
        # Test updating arrived quantity
        data = {f"product_arrived_{self.product.id}": "5.00"}
        response = self.client.post(reverse("view_order_totals"), data)
        self.assertEqual(response.status_code, 200)

        self.product.refresh_from_db()
        self.assertEqual(self.product.arrived_quantity, Decimal("5.00"))

        # Check that order status is updated if arrived quantity is 0
        data_zero = {f"product_arrived_{self.product.id}": "0"}
        self.client.post(reverse("view_order_totals"), data_zero)
        self.product.refresh_from_db()
        self.assertEqual(self.product.arrived_quantity, 0)

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 10)  # STATUS_DID_NOT_ARRIVE

    def test_count_initial_cash_get(self):
        response = self.client.get(reverse("count_initial_cash"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "distribution/count_initial_cash.html")

    def test_count_initial_cash_post(self):
        data = {"initial-cash": "100.50"}
        response = self.client.post(reverse("count_initial_cash"), data)
        self.assertEqual(response.status_code, 200)

        account_detail = DistributionAccountDetail.objects.filter(date=self.today).first()
        self.assertIsNotNone(account_detail)
        self.assertEqual(account_detail.initial_amount, Decimal("100.50"))

    def test_view_basket_counts_get(self):
        # Ensure the product is for today for this view to show something relevant if it filters by today
        # The view uses libs.get_today() for filtering orders.
        # So we need a product distributed TODAY.
        product_today = Product.objects.create(
            name="Today Product",
            category=self.category,
            price=Decimal("5.00"),
            unit="kg",
            distribution_date=self.today,
            order_limit_date=timezone.now() - datetime.timedelta(days=1),
            total_quantity=Decimal("10.00"),
            arrived_quantity=Decimal("10.00"),
        )
        Order.objects.create(
            user=self.user, product=product_today, quantity=Decimal("2.00"), arrived_quantity=Decimal("2.00"), status=0
        )

        response = self.client.get(reverse("view_basket_counts"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "distribution/view_basket_counts.html")
        # Check if user is in the summary
        self.assertContains(response, "Test User")

    def test_view_product_orders_get(self):
        # Need a product for today
        product_today = Product.objects.create(
            name="Today Product 2",
            category=self.category,
            price=Decimal("5.00"),
            unit="kg",
            distribution_date=self.today,
            order_limit_date=timezone.now() - datetime.timedelta(days=1),
            total_quantity=Decimal("10.00"),
            arrived_quantity=Decimal("10.00"),
        )

        # Default view (redirects or shows first product)
        # The URL regex requires an argument: r'^dist/([0-9]+)/$'
        response = self.client.get(reverse("view_product_orders", args=[1]))
        # It might redirect or show the first product depending on logic
        # The view logic: if product_no='', it defaults to 1.
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "distribution/view_product_orders.html")

        # View specific product
        response = self.client.get(reverse("view_product_orders", args=[1]))
        self.assertEqual(response.status_code, 200)

    def test_member_payment_get(self):
        # Create order for today
        product_today = Product.objects.create(
            name="Today Product Payment",
            category=self.category,
            price=Decimal("5.00"),
            unit="kg",
            distribution_date=self.today,
            order_limit_date=timezone.now() - datetime.timedelta(days=1),
            total_quantity=Decimal("10.00"),
            arrived_quantity=Decimal("10.00"),
        )
        Order.objects.create(
            user=self.user, product=product_today, quantity=Decimal("2.00"), arrived_quantity=Decimal("2.00"), status=0
        )

        response = self.client.get(reverse("member_payment"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "distribution/member_payment.html")
        self.assertContains(response, "Test User")

    def test_member_payment_post(self):
        # Create order for today
        product_today = Product.objects.create(
            name="Today Product Payment POST",
            category=self.category,
            price=Decimal("10.00"),
            unit="kg",
            distribution_date=self.today,
            order_limit_date=timezone.now() - datetime.timedelta(days=1),
            total_quantity=Decimal("10.00"),
            arrived_quantity=Decimal("10.00"),
        )
        Order.objects.create(
            user=self.user, product=product_today, quantity=Decimal("1.00"), arrived_quantity=Decimal("1.00"), status=0
        )

        # Total price should be 10.00

        data = {"form-name": "payment-form", "member-id": self.user.id, "amount-paid": "10.00"}

        response = self.client.post(reverse("member_payment"), data)
        self.assertEqual(response.status_code, 200)

        # Check payment created
        # Payment date stores datetime, so exact match with date might fail if not handled correctly by Django or if logic uses now()
        # The view uses libs.get_now() for payment.date, which is a datetime.
        # But the filter in view uses date__gte=today.
        # Let's check if we can find it with date__date=today or just filter by user and order by date
        payment = Payment.objects.filter(user=self.user).last()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.date.date(), self.today)
        self.assertEqual(payment.amount, Decimal("10.00"))

        # Check debt (should be 0)
        debt = Debt.objects.filter(user=self.user, payment=payment).first()
        self.assertIsNotNone(debt)
        # The setUp created an order for 20.00 which is unpaid.
        # This test created another order for 10.00.
        # Total to pay = 20.00 + 10.00 = 30.00
        # Paid = 10.00
        # Expected Debt = 20.00

        # Check debt
        debt = Debt.objects.filter(user=self.user, payment=payment).first()
        self.assertIsNotNone(debt)
        self.assertEqual(debt.amount, Decimal("20.00"))

    def test_account_summary_get(self):
        response = self.client.get(reverse("account_summary"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "distribution/account_summary.html")

    def test_account_summary_post(self):
        data = {"final-amount": "500.00", "notes": "Test notes"}
        response = self.client.post(reverse("account_summary"), data)
        self.assertEqual(response.status_code, 200)

        account_detail = DistributionAccountDetail.objects.filter(date=self.today).first()
        self.assertIsNotNone(account_detail)
        self.assertEqual(account_detail.final_amount, Decimal("500.00"))
        self.assertEqual(account_detail.notes, "Test notes")
