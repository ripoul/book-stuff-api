from django.conf import settings
from django.db import models
from model_utils import FieldTracker

from booking.constants.invitation import PlaceInvitationStatus
from booking.models.base import UUIDPrimaryKeyModel
from booking.models.place import Place


class PlaceInvitation(UUIDPrimaryKeyModel):
    place = models.ForeignKey(
        Place,
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    email = models.EmailField()
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="place_invitations_sent",
    )
    status = models.CharField(
        max_length=16,
        choices=PlaceInvitationStatus.choices,
        default=PlaceInvitationStatus.PENDING,
    )
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="place_invitations_accepted",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    tracker = FieldTracker(fields=["status"])

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("place", "email"),
                name="booking_placeinvitation_unique_place_email",
            ),
        ]
