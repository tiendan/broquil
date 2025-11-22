from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import Client, TestCase
from django.urls import reverse
from elbroquil import models


class ManagementViewsTest(TestCase):
    def setUp(self):
        self.client = Client()

        # Create a user with accounting permission
        content_type = ContentType.objects.get_for_model(models.DistributionAccountDetail)
        permission = Permission.objects.create(
            codename="accounting",
            name="Can view accounting",
            content_type=content_type,
        )
        self.user = User.objects.create_user(username="testuser@example.com", password="password")
        self.user.user_permissions.add(permission)
        self.user.save()

        self.client.login(username="testuser@example.com", password="password")

        # Create distribution account detail
        self.distribution_detail = models.DistributionAccountDetail.objects.create(
            date=date.today(), initial_amount=Decimal("100.00"), final_amount=Decimal("150.00")
        )

        # Create payment and debt
        self.payment = models.Payment.objects.create(user=self.user, date=date.today(), amount=Decimal("50.00"))

        self.debt = models.Debt.objects.create(user=self.user, payment=self.payment, amount=Decimal("10.00"))

    def test_view_distribution_detail_get(self):
        """Test distribution detail view"""
        response = self.client.get(reverse("view_distribution_detail"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "management/view_distribution_detail.html")
        # The view returns distribution_dates, not distribution_details
        self.assertIn("distribution_dates", response.context)

    def test_view_distribution_task_information_get(self):
        """Test distribution task information view"""
        response = self.client.get(reverse("view_distribution_task_information"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "management/view_distribution_task_information.html")

    @patch("elbroquil.views.management_views.libs.update_distribution_task_information")
    def test_view_distribution_task_information_post(self, mock_update):
        """Test updating distribution task information"""
        mock_update.return_value = "Update successful"

        response = self.client.post(
            reverse("view_distribution_task_information"), {"form-name": "update-form", "year": "2023"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(mock_update.called)

    def test_view_debts_get(self):
        """Test viewing debts"""
        response = self.client.get(reverse("view_debts"))
        self.assertEqual(response.status_code, 200)
        # Note: uses fee/view_debts.html not management/view_debts.html
        self.assertTemplateUsed(response, "fee/view_debts.html")
        self.assertIn("user_debts", response.context)

    def test_view_accounting_detail_get(self):
        """Test viewing accounting detail"""
        response = self.client.get(reverse("view_accounting_detail"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "management/view_accounting_detail.html")
        # Returns start_date and end_date, not distribution_details
        self.assertIn("start_date", response.context)
        self.assertIn("end_date", response.context)
