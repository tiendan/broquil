import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import elbroquil.libraries as libs
import elbroquil.tasks as tasks
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from elbroquil.models import Category, DistributionDate, EmailTemplate, Order, Producer, Product


class TasksTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password", email="user@example.com")

        self.producer = Producer.objects.create(
            company_name="Test Producer", email="producer@example.com", active=True, order_hour=12
        )
        self.category = Category.objects.create(name="Test Category", producer=self.producer)

        self.next_dist_date = libs.get_next_distribution_date()
        DistributionDate.objects.get_or_create(distribution_date=self.next_dist_date, canceled=False)

    @patch("elbroquil.libraries.send_email_to_address")
    def test_send_order_to_producers(self, mock_send_email):
        # Create a product that needs to be ordered
        product = Product.objects.create(
            name="Test Product",
            category=self.category,
            price=Decimal("10.00"),
            unit="kg",
            distribution_date=self.next_dist_date,
            order_limit_date=timezone.now() - datetime.timedelta(hours=1),  # Order limit passed
            sent_to_producer=False,
        )

        Order.objects.create(
            user=self.user, product=product, quantity=Decimal("5.00"), arrived_quantity=Decimal("5.00"), status=0
        )

        tasks.send_order_to_producers()

        # Verify email sent
        self.assertTrue(mock_send_email.called)
        args, _ = mock_send_email.call_args
        self.assertIn("producer@example.com", args[2])

        # Verify product updated
        product.refresh_from_db()
        self.assertTrue(product.sent_to_producer)
        self.assertEqual(product.total_quantity, Decimal("5.00"))

    @patch("elbroquil.libraries.send_email_to_active_users")
    @patch("elbroquil.tasks.download_cal_rosset_excel")
    @patch("xlrd.open_workbook")
    @patch("elbroquil.parse.parse_cal_rosset")
    def test_create_offer(self, mock_parse, mock_open_workbook, mock_download, mock_send_email):
        # Mock dependencies
        mock_download.return_value = "/tmp/test.xls"
        mock_parse.return_value = [["Category 1", "Product 1", 1.50, "kg", "Origin 1", "Comments 1"]]
        mock_send_email.return_value = [1]  # 1 person emailed

        # Ensure we are within the window to create an offer (mocking time might be needed if test runs on wrong day)
        # For simplicity, we assume the test environment allows it or we'd need to mock libs.get_today/get_next_distribution_date

        # Create Cal Rosset producer
        cal_rosset = Producer.objects.create(
            company_name="Cal Rosset", email="calrosset@example.com", excel_format=1, order_hour=12  # CAL_ROSSET
        )

        with patch("os.remove"):  # Prevent trying to remove the fake file
            tasks.create_offer()

        # Verify product created
        product = Product.objects.filter(name="Product 1").first()
        self.assertIsNotNone(product)
        self.assertEqual(product.price, Decimal("1.50"))
        self.assertEqual(product.category.producer, cal_rosset)

    @patch("elbroquil.libraries.send_email_to_active_users")
    def test_send_sunday_reminder(self, mock_send_email):
        # Create a product for next distribution
        Product.objects.create(
            name="Test Product",
            category=self.category,
            price=Decimal("10.00"),
            unit="kg",
            distribution_date=libs.get_next_weekday(),  # Wednesday
            order_limit_date=timezone.now() + datetime.timedelta(days=1),
        )

        mock_send_email.return_value = [1]

        tasks.send_sunday_reminder()

        self.assertTrue(mock_send_email.called)

    @patch("elbroquil.libraries.send_email_with_cc")
    @patch("elbroquil.libraries.update_distribution_task_information")
    def test_send_task_reminder(self, mock_update_info, mock_send_email):
        # Mock update info
        mock_update_info.return_value = "Updated"

        # Create a task for the near future
        from elbroquil.models import DistributionTask

        task_date = timezone.now().date() + datetime.timedelta(days=3)
        DistributionTask.objects.create(user=self.user, distribution_date=task_date)

        tasks.send_task_reminder()

        self.assertTrue(mock_send_email.called)
        args, _ = mock_send_email.call_args
        self.assertIn(self.user.email, args[2])
