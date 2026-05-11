from django.contrib.auth.models import User
from django_filters.rest_framework import DjangoFilterBackend
from guardian.shortcuts import get_objects_for_user
from rest_framework import mixins
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter
from rest_framework.viewsets import GenericViewSet

from booking.constants.invitation import PlaceInvitationStatus
from booking.filter import ManagerInvitationFilter, MyInvitationFilter
from booking.models import Place, PlaceInvitation
from booking.permissions import ManagerInvitationPermission, MyInvitationPermission
from booking.serializers.invitation import (
    ManagerInvitationSerializer,
    MyInvitationSerializer,
)


class MyInvitationViewSet(
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    serializer_class = MyInvitationSerializer
    permission_classes = [MyInvitationPermission]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = MyInvitationFilter
    ordering_fields = ["created_at", "updated_at"]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return PlaceInvitation.objects.none()
        assert isinstance(user, User)
        if not user.email:
            return PlaceInvitation.objects.none()
        return PlaceInvitation.objects.filter(email__iexact=user.email).select_related(
            "place"
        )

    def perform_update(self, serializer):
        new_status = serializer.validated_data.get("status")
        if new_status == PlaceInvitationStatus.ACCEPTED:
            serializer.save(accepted_by=self.request.user)
            return
        serializer.save()


class ManagerInvitationViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    serializer_class = ManagerInvitationSerializer
    permission_classes = [ManagerInvitationPermission]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ManagerInvitationFilter
    ordering_fields = ["created_at", "updated_at"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return PlaceInvitation.objects.none()
        managed_places = get_objects_for_user(
            user,
            "booking.manage_place",
            Place,
        )
        return PlaceInvitation.objects.filter(place__in=managed_places).select_related(
            "place"
        )

    def perform_create(self, serializer):
        user = self.request.user
        assert isinstance(user, User)
        place = serializer.validated_data["place"]
        if not user.has_perm("booking.manage_place", place):
            raise PermissionDenied("You do not manage this place.")
        serializer.save(invited_by=user)
