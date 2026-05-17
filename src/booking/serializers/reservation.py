from datetime import datetime

from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import serializers

from booking.models import Reservation, Resource


class IsoAwareDateTimeField(serializers.DateTimeField):
    default_error_messages = {
        **serializers.DateTimeField.default_error_messages,
        "naive": "Datetime must include timezone offset.",
    }

    def to_internal_value(self, data):
        if isinstance(data, str):
            parsed = parse_datetime(data.strip())
            if parsed is not None and not timezone.is_aware(parsed):
                self.fail("naive")
        elif isinstance(data, datetime) and not timezone.is_aware(data):
            self.fail("naive")
        return super().to_internal_value(data)


class ReservationSerializer(serializers.ModelSerializer):
    resource = serializers.PrimaryKeyRelatedField(queryset=Resource.objects.all())
    starts_at = IsoAwareDateTimeField()
    ends_at = IsoAwareDateTimeField()

    class Meta:
        model = Reservation
        fields = (
            "id",
            "resource",
            "starts_at",
            "ends_at",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_by", "created_at", "updated_at")

    def validate(self, attrs):
        resource = attrs.get("resource")
        starts_at = attrs.get("starts_at")
        ends_at = attrs.get("ends_at")
        if self.instance is not None:
            resource = resource if resource is not None else self.instance.resource
            starts_at = starts_at if starts_at is not None else self.instance.starts_at
            ends_at = ends_at if ends_at is not None else self.instance.ends_at
        if starts_at is not None and ends_at is not None and starts_at >= ends_at:
            raise serializers.ValidationError(
                {"ends_at": ["ends_at must be after starts_at."]}
            )
        if resource is None or starts_at is None or ends_at is None:
            return attrs
        overlap = Q(
            starts_at__lt=ends_at,
            ends_at__gt=starts_at,
        )
        qs = Reservation.objects.filter(resource=resource).filter(overlap)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                {
                    "non_field_errors": [
                        "This time range overlaps an existing reservation."
                    ]
                }
            )
        return attrs
