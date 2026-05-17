from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from rest_framework.viewsets import ModelViewSet

from booking.filter import ResourceFilter
from booking.models import Resource
from booking.permissions import ResourcePermission
from booking.serializers.resource import ResourceSerializer


class ResourceViewSet(ModelViewSet):
    serializer_class = ResourceSerializer
    permission_classes = [ResourcePermission]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ResourceFilter
    ordering_fields = ["name", "created_at", "id"]

    def get_queryset(self):
        return Resource.objects.visible_for(self.request.user)
