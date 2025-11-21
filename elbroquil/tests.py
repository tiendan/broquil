from django.test import TestCase, Client
from django.urls import reverse

class SmokeTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_root_url(self):
        response = self.client.get(reverse('site_root'))
        # It might redirect to login if not authenticated, or show the page
        self.assertIn(response.status_code, [200, 302])

    def test_login_page(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_translation_tags(self):
        response = self.client.get(reverse('contact'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        if "{% trans" in content:
            print("FOUND LITERAL TRANS TAG IN OUTPUT")
            print(content)
        self.assertNotIn("{% trans", content)

