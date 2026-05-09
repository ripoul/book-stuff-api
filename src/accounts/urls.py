from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounts.views import UserViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")

urlpatterns = [
    path("", include(router.urls)),
]
