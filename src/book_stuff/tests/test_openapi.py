from django.test import TestCase
from django.urls import reverse


class OpenAPISchemaPublicTests(TestCase):
    def test_schema_anonymous_ok(self):
        response = self.client.get(reverse("schema"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("openapi", response.content.decode().lower())

    def test_swagger_ui_anonymous_ok(self):
        response = self.client.get(reverse("swagger-ui"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("swagger", response.content.decode().lower())
