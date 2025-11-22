import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone
from elbroquil import models


class ProductViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()

        # Create a user with necessary permissions
        content_type = ContentType.objects.get_for_model(models.Product)
        permission = Permission.objects.create(
            codename="modify_products",
            name="Can modify products",
            content_type=content_type,
        )
        self.user = User.objects.create_user(username="testuser", password="password")
        self.user.user_permissions.add(permission)
        self.user.save()

        self.client.login(username="testuser", password="password")

        # Create a producer
        self.producer = models.Producer.objects.create(
            company_name="Test Producer",
            first_name="Test",
            email="producer@test.com",
            order_hour=12,
            excel_format=models.STANDARD,
        )

        # Create a category
        self.category = models.Category.objects.create(name="Test Category", producer=self.producer)

    def test_upload_products_get(self):
        response = self.client.get(reverse("upload_products"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "product/upload_products.html")

    @patch("elbroquil.views.product_views.xlrd.open_workbook")
    @patch("elbroquil.views.product_views.parser.parse_standard")
    @patch("builtins.open", new_callable=MagicMock)
    def test_check_products_post_valid(self, mock_open, mock_parse, mock_open_workbook):
        # Mock parser return
        mock_parse.return_value = (
            [("Category", "Product", "1.50", "kg", "Origin", "Comments")],  # products
            "2025-10-25",  # distribution_date
            "2025-10-23 12:00",  # order_limit_date
        )

        excel_file = SimpleUploadedFile("products.xls", b"file_content", content_type="application/vnd.ms-excel")

        data = {"producer": self.producer.id, "excel_file": excel_file}

        response = self.client.post(reverse("check_products"), data)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "product/check_product_info.html")
        self.assertIn("products", response.context)
        self.assertEqual(len(response.context["products"]), 1)

    def test_confirm_products_post(self):
        # Prepare data simulating the form submission from check_products
        table_data = "[('Test Category', 'Test Product', '1.50', 'kg', 'Origin', 'Comments')]"

        data = {
            "table_data": table_data,
            "producer_id": self.producer.id,
            "distribution_date": "2023-10-25",
            "order_limit_date": "2023-10-23 12:00",
        }

        response = self.client.post(reverse("confirm_products"), data)

        # Should redirect to view_products
        self.assertRedirects(response, reverse("view_products", args=(self.producer.id,)))

        # Check if product was created
        self.assertTrue(models.Product.objects.filter(name="Test Product").exists())
        product = models.Product.objects.get(name="Test Product")
        self.assertEqual(product.price, Decimal("1.50"))
        self.assertEqual(product.category.name, "Test Category")

    def test_view_products_get(self):
        # Create a product to view
        models.Product.objects.create(
            name="Existing Product",
            category=self.category,
            price=Decimal("2.00"),
            unit="kg",
            distribution_date=None,  # Template product
        )

        response = self.client.get(reverse("view_products", args=(self.producer.id,)))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "product/view_defined_products.html")
        self.assertIn("products", response.context)
        # The view returns zipped products, so we check length
        self.assertEqual(len(response.context["products"]), 1)
