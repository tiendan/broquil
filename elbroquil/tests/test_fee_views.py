from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import Client, TestCase
from django.urls import reverse
from elbroquil import models


class FeeViewsTest(TestCase):
    def setUp(self):
        self.client = Client()

        # Create a user with accounting permission
        content_type = ContentType.objects.get_for_model(models.Quarterly)
        permission = Permission.objects.create(
            codename="accounting",
            name="Can view accounting",
            content_type=content_type,
        )
        self.user = User.objects.create_user(username="testuser@example.com", password="password")
        self.user.user_permissions.add(permission)
        self.user.save()

        self.client.login(username="testuser@example.com", password="password")

        # Create quarterly fees
        self.quarterly = models.Quarterly.objects.create(user=self.user, year=2023, quarter=3, amount=Decimal("25.00"))

    def test_view_fees_get(self):
        """Test viewing fees page"""
        response = self.client.get(reverse("view_fees"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "fee/view_fees.html")
        self.assertIn("users", response.context)
        self.assertIn("quarters", response.context)

    def test_view_fees_post_quarter_form(self):
        """Test filtering fees by quarter"""
        response = self.client.post(reverse("view_fees"), {"form-name": "quarter-form", "quarter": "2023_3"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("filtered_quarterly_fees", response.context)
        self.assertEqual(len(response.context["filtered_quarterly_fees"]), 1)

    def test_view_fees_post_member_form(self):
        """Test viewing member fee history"""
        response = self.client.post(reverse("view_fees"), {"form-name": "member-form", "member_id": self.user.id})

        self.assertEqual(response.status_code, 200)
        self.assertIn("member_fees", response.context)

    def test_create_fees_get(self):
        """Test create fees page GET"""
        response = self.client.get(reverse("create_fees"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "fee/create_fees.html")
        self.assertIn("users", response.context)
        self.assertIn("year", response.context)
        self.assertIn("quarter", response.context)

    def test_create_fees_post_success(self):
        """Test creating fees successfully"""
        user2 = User.objects.create_user(username="user2@example.com", password="password")

        response = self.client.post(reverse("create_fees"), {"user_ids": [user2.id], "fee_amount": "30.00"})

        self.assertEqual(response.status_code, 200)
        # Verify fee was created
        self.assertTrue(models.Quarterly.objects.filter(user=user2).exists())

    def test_create_fees_post_no_members(self):
        """Test creating fees with no members selected"""
        response = self.client.post(reverse("create_fees"), {"user_ids": [], "fee_amount": "30.00"})

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context["alert_message"])
