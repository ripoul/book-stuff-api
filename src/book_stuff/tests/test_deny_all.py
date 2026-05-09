from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from book_stuff.permissions import DenyAll


class DenyAllView(APIView):
    permission_classes = [DenyAll]

    def get(self, request):
        return Response({"ok": True})


class DenyAllPermissionTests(TestCase):
    def test_denies_authenticated_get(self):
        user = User.objects.create_user(username="deny-u", password="p")
        factory = APIRequestFactory()
        request = factory.get("/")
        force_authenticate(request, user=user)
        response = DenyAllView.as_view()(request)
        self.assertEqual(response.status_code, 403)
