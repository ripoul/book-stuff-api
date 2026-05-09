from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class JWTCreateViewTests(APITestCase):
    def setUp(self):
        User.objects.create_user(username="jwt-user", password="secret-pass")

    def test_obtain_returns_access_and_refresh(self):
        response = self.client.post(
            reverse("jwt-create"),
            {"username": "jwt-user", "password": "secret-pass"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_obtain_rejects_wrong_password(self):
        response = self.client.post(
            reverse("jwt-create"),
            {"username": "jwt-user", "password": "wrong"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_obtain_rejects_unknown_user(self):
        response = self.client.post(
            reverse("jwt-create"),
            {"username": "nobody", "password": "x"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class JWTRefreshViewTests(APITestCase):
    def setUp(self):
        User.objects.create_user(username="refresh-user", password="secret-pass")

    def test_refresh_returns_new_access(self):
        create_r = self.client.post(
            reverse("jwt-create"),
            {"username": "refresh-user", "password": "secret-pass"},
            format="json",
        )
        self.assertEqual(create_r.status_code, status.HTTP_200_OK)
        refresh = create_r.data["refresh"]
        response = self.client.post(
            reverse("jwt-refresh"),
            {"refresh": refresh},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertNotEqual(response.data["access"], create_r.data["access"])

    def test_refresh_rejects_invalid_token(self):
        response = self.client.post(
            reverse("jwt-refresh"),
            {"refresh": "not-a-valid.jwt.token"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
