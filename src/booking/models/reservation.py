from django.conf import settings
from django.db import models

from booking.models.base import UUIDPrimaryKeyModel
from booking.models.resource import Resource


class Reservation(UUIDPrimaryKeyModel):
    resource = models.ForeignKey(
        Resource,
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(starts_at__lt=models.F("ends_at")),
                name="reservation_starts_before_ends",
            ),
        ]
        indexes = [
            models.Index(fields=["resource", "starts_at"]),
        ]

    def __str__(self) -> str:
        return f"[{self.resource.place.name}] {self.resource.name} {self.starts_at}–{self.ends_at}"
