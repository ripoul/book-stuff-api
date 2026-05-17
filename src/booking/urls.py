from django.urls import include, path
from rest_framework.routers import DefaultRouter

from booking.views.invitation import ManagerInvitationViewSet, MyInvitationViewSet
from booking.views.place import PlaceViewSet
from booking.views.reservation import ReservationViewSet
from booking.views.resource import ResourceViewSet

router = DefaultRouter()
router.register("places", PlaceViewSet, basename="place")
router.register("resources", ResourceViewSet, basename="resource")
router.register("reservations", ReservationViewSet, basename="reservation")
router.register("me/invitations", MyInvitationViewSet, basename="my-invitation")
router.register(
    "manage/invitations", ManagerInvitationViewSet, basename="manager-invitation"
)

urlpatterns = [
    path("", include(router.urls)),
]
