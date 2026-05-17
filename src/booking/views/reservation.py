from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from rest_framework.viewsets import ModelViewSet

from booking.filter.reservation import ReservationFilter
from booking.models import Resource, Reservation
from booking.permissions import ReservationPermission
from booking.serializers.reservation import ReservationSerializer


class ReservationViewSet(ModelViewSet):
    serializer_class = ReservationSerializer
    permission_classes = [ReservationPermission]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ReservationFilter
    ordering_fields = ["starts_at", "ends_at", "created_at", "id"]

    def get_queryset(self):
        return Reservation.objects.filter(
            resource__in=Resource.objects.visible_for(self.request.user)
        ).select_related(
            "resource",
            "resource__place",
            "created_by",
        )

    def perform_create(self, serializer):
        resource = serializer.validated_data["resource"]
        with transaction.atomic():
            Resource.objects.select_for_update().get(pk=resource.pk)
            serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        resource = serializer.validated_data.get(
            "resource", serializer.instance.resource
        )
        with transaction.atomic():
            Resource.objects.select_for_update().get(pk=resource.pk)
            serializer.save()
