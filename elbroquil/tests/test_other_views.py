from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from elbroquil import models


class OtherViewsTest(TestCase):
    def setUp(self):
        self.client = Client()

        # Create a user
        self.user = User.objects.create_user(username="testuser@example.com", password="password")
        self.client.login(username="testuser@example.com", password="password")

        # Create a producer
        self.producer = models.Producer.objects.create(
            company_name="Test Producer",
            first_name="Test",
            email="producer@test.com",
            order_hour=12,
            active=True,
            description="Test description",
        )

        # Create an email list
        self.email_list = models.EmailList.objects.create(
            name="Test List", email_addresses="test1@example.com,test2@example.com"
        )

    def test_set_language_post(self):
        """Test language switching"""
        response = self.client.post(reverse("set_language"), {"language": "es"})
        self.assertEqual(response.status_code, 302)  # Should redirect
        self.assertEqual(self.client.session.get("django_language"), "es")

    def test_set_language_get(self):
        """Test language switching via GET"""
        response = self.client.get(reverse("set_language"), {"language": "en"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session.get("django_language"), "en")

    @patch("elbroquil.views.other_views.libs.send_email_with_cc")
    def test_contact_get(self, mock_send_email):
        """Test contact form GET request"""
        response = self.client.get(reverse("contact"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "contact.html")
        self.assertIn("to_lists", response.context)

    @patch("elbroquil.views.other_views.libs.send_email_with_cc")
    def test_contact_post_to_list(self, mock_send_email):
        """Test sending message to an email list"""
        response = self.client.post(
            reverse("contact"), {"to-list": self.email_list.id, "date": "2023-10-25", "message": "Test message"}
        )

        self.assertEqual(response.status_code, 302)  # Redirects after successful POST
        self.assertTrue(mock_send_email.called)
        # Verify email was sent with correct parameters
        call_args = mock_send_email.call_args
        self.assertIn("Test message", call_args[0][1])

    def test_producer_info_all(self):
        """Test producer info page showing all producers"""
        response = self.client.get(reverse("producer_info"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "producer/producer_info.html")
        self.assertIn("producers", response.context)
        self.assertEqual(len(response.context["producers"]), 1)

    @patch("elbroquil.views.other_views.send_order_to_producers")
    def test_tasks_endpoint(self, mock_send_order):
        """Test tasks endpoint execution"""
        response = self.client.get(reverse("tasks"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(mock_send_order.called)
