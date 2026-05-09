from django_filters.rest_framework import DjangoFilterBackend
from guardian.shortcuts import assign_perm, get_objects_for_user
from rest_framework.filters import OrderingFilter
from rest_framework.viewsets import ModelViewSet

from booking.filter import PlaceFilter
from booking.models import Place
from booking.permissions import PlacePermission
from booking.serializers.place import PlaceSerializer


class PlaceViewSet(ModelViewSet):
    serializer_class = PlaceSerializer
    permission_classes = [PlacePermission]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = PlaceFilter
    ordering_fields = ["name", "created_at", "id"]

    def get_queryset(self):
        public_qs = Place.objects.filter(public=True)
        user = self.request.user
        if not user.is_authenticated:
            return public_qs
        private_with_access = get_objects_for_user(
            user,
            ["booking.can_see", "booking.manage_place"],
            Place,
            any_perm=True,
        )
        return (public_qs | private_with_access).distinct()

    def perform_create(self, serializer):
        place = serializer.save()
        assign_perm("booking.manage_place", self.request.user, place)
