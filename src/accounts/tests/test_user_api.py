from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class UserCreateAPITests(APITestCase):
    def test_create_user_anonymous(self):
        response = self.client.post(
            reverse("user-list"),
            {
                "email": "newbie@example.com",
                "password": "longsecret1",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        u = User.objects.get(email="newbie@example.com")
        self.assertEqual(u.username, "newbie@example.com")

    def test_create_user_with_first_and_last_name(self):
        response = self.client.post(
            reverse("user-list"),
            {
                "email": "named@example.com",
                "password": "longsecret1",
                "first_name": "Jean",
                "last_name": "Dupont",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        u = User.objects.get(email="named@example.com")
        self.assertEqual(u.first_name, "Jean")
        self.assertEqual(u.last_name, "Dupont")
        self.assertEqual(response.data["first_name"], "Jean")
        self.assertEqual(response.data["last_name"], "Dupont")


class UserRetrieveUpdateAPITests(APITestCase):
    def setUp(self):
        self.me = User.objects.create_user(
            username="me@example.com",
            email="me@example.com",
            password="mypassword1",
        )
        self.other = User.objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="otherpass1",
        )

    def test_retrieve_self_requires_auth(self):
        url = reverse("user-detail", kwargs={"pk": self.me.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_self_ok(self):
        self.client.force_authenticate(user=self.me)
        url = reverse("user-detail", kwargs={"pk": self.me.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "me@example.com")
        self.assertEqual(response.data["email"], "me@example.com")
        self.assertEqual(response.data["first_name"], "")
        self.assertEqual(response.data["last_name"], "")

    def test_retrieve_other_returns_404(self):
        self.client.force_authenticate(user=self.me)
        url = reverse("user-detail", kwargs={"pk": self.other.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_self_syncs_username_with_email(self):
        self.client.force_authenticate(user=self.me)
        url = reverse("user-detail", kwargs={"pk": self.me.pk})
        response = self.client.patch(
            url,
            {"email": "newemail@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.me.refresh_from_db()
        self.assertEqual(self.me.email, "newemail@example.com")
        self.assertEqual(self.me.username, "newemail@example.com")

    def test_patch_self_updates_first_and_last_name(self):
        self.client.force_authenticate(user=self.me)
        url = reverse("user-detail", kwargs={"pk": self.me.pk})
        response = self.client.patch(
            url,
            {"first_name": "Marie", "last_name": "Martin"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.me.refresh_from_db()
        self.assertEqual(self.me.first_name, "Marie")
        self.assertEqual(self.me.last_name, "Martin")
        self.assertEqual(response.data["first_name"], "Marie")
        self.assertEqual(response.data["last_name"], "Martin")
        self.client.force_authenticate(user=self.me)
        url = reverse("user-detail", kwargs={"pk": self.other.pk})
        response = self.client.patch(
            url,
            {"email": "hack@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
