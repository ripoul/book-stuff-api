from django_filters.rest_framework import DjangoFilterBackend
from guardian.shortcuts import get_objects_for_user
from rest_framework.filters import OrderingFilter
from rest_framework.viewsets import ModelViewSet

from booking.filter import ResourceFilter
from booking.models import Place, Resource
from booking.permissions import ResourcePermission
from booking.serializers.resource import ResourceSerializer


class ResourceViewSet(ModelViewSet):
    serializer_class = ResourceSerializer
    permission_classes = [ResourcePermission]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ResourceFilter
    ordering_fields = ["name", "created_at", "id"]

    def get_queryset(self):
        user = self.request.user
        public_places = Place.objects.filter(public=True)
        if not user.is_authenticated:
            return Resource.objects.filter(place__in=public_places).select_related(
                "place"
            )
        private_places = get_objects_for_user(
            user,
            ["booking.can_see", "booking.manage_place"],
            Place,
            any_perm=True,
        )
        visible_places = (public_places | private_places).distinct()
        return Resource.objects.filter(place__in=visible_places).select_related("place")
