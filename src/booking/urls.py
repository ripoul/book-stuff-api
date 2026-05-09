from django.urls import include, path
from rest_framework.routers import DefaultRouter

from booking.views.place import PlaceViewSet
from booking.views.resource import ResourceViewSet

router = DefaultRouter()
router.register("places", PlaceViewSet, basename="place")
router.register("resources", ResourceViewSet, basename="resource")

urlpatterns = [
    path("", include(router.urls)),
]
