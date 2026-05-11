from django.db.models.signals import post_save
from django.dispatch import receiver
from guardian.shortcuts import assign_perm, remove_perm

from booking.constants.invitation import PlaceInvitationStatus
from booking.models.invitation import PlaceInvitation


@receiver(post_save, sender=PlaceInvitation)
def sync_can_see_permission(
    sender: type[PlaceInvitation],
    instance: PlaceInvitation,
    created: bool,
    **kwargs: object,
) -> None:
    previous_status = instance.tracker.previous("status")
    status_changed = created or instance.tracker.has_changed("status")

    if (
        status_changed
        and instance.status == PlaceInvitationStatus.ACCEPTED
        and instance.accepted_by is not None
    ):
        assign_perm("booking.can_see", instance.accepted_by, instance.place)
        return

    if (
        previous_status == PlaceInvitationStatus.ACCEPTED
        and instance.status != PlaceInvitationStatus.ACCEPTED
        and instance.accepted_by is not None
    ):
        remove_perm("booking.can_see", instance.accepted_by, instance.place)
