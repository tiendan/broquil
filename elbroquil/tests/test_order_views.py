from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from elbroquil import models


class OrderViewsTest(TestCase):
    def setUp(self):
        self.client = Client()

        # Create a member user (with @ in username)
        self.user = User.objects.create_user(
            username="testuser@example.com", password="password", first_name="Test", last_name="User"
        )
        self.client.login(username="testuser@example.com", password="password")

        # Create a producer and category
        self.producer = models.Producer.objects.create(
            company_name="Test Producer", first_name="Test", email="producer@test.com", order_hour=12
        )

        self.category = models.Category.objects.create(name="Test Category", producer=self.producer)

        # Create a product
        self.product = models.Product.objects.create(
            name="Test Product",
            category=self.category,
            price=Decimal("10.00"),
            unit="kg",
            distribution_date=date.today() + timedelta(days=7),
            order_limit_date=timezone.now() + timedelta(days=5),
        )

        # Create a payment
        self.payment = models.Payment.objects.create(user=self.user, date=timezone.now(), amount=Decimal("50.00"))

    def test_order_history_get(self):
        """Test order history page GET"""
        response = self.client.get(reverse("order_history"))
        self.assertEqual(response.status_code, 200)
        # Actual template is order/order_history.html
        self.assertTemplateUsed(response, "order/order_history.html")

    def test_view_order_get(self):
        """Test view order page"""
        response = self.client.get(reverse("view_order"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "order/view_order.html")
        # Returns category_count not categories
        self.assertIn("category_count", response.context)

    def test_update_order_get(self):
        """Test update order page GET"""
        response = self.client.get(reverse("update_order", args=(1,)))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "order/update_order.html")
