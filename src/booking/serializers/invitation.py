from rest_framework import serializers

from booking.constants.invitation import PlaceInvitationStatus
from booking.models import PlaceInvitation

USER_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    PlaceInvitationStatus.PENDING: {
        PlaceInvitationStatus.ACCEPTED,
        PlaceInvitationStatus.DECLINED,
    },
    PlaceInvitationStatus.ACCEPTED: {PlaceInvitationStatus.DECLINED},
    PlaceInvitationStatus.DECLINED: {PlaceInvitationStatus.ACCEPTED},
}

MANAGER_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    PlaceInvitationStatus.PENDING: {PlaceInvitationStatus.REVOKED},
    PlaceInvitationStatus.ACCEPTED: {PlaceInvitationStatus.REVOKED},
    PlaceInvitationStatus.DECLINED: {PlaceInvitationStatus.REVOKED},
    PlaceInvitationStatus.REVOKED: {PlaceInvitationStatus.PENDING},
}


class MyInvitationSerializer(serializers.ModelSerializer):
    place_name = serializers.CharField(source="place.name", read_only=True)

    class Meta:
        model = PlaceInvitation
        fields = (
            "id",
            "place",
            "place_name",
            "email",
            "status",
            "accepted_by",
            "invited_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "place",
            "place_name",
            "email",
            "accepted_by",
            "invited_by",
            "created_at",
            "updated_at",
        )

    def validate_status(self, value: str) -> str:
        instance: PlaceInvitation | None = self.instance
        if instance is None:
            raise serializers.ValidationError("Cannot create an invitation here.")
        allowed = USER_ALLOWED_TRANSITIONS.get(instance.status, set())
        if value not in allowed:
            raise serializers.ValidationError(
                f"Transition from {instance.status} to {value} is not allowed."
            )
        return value


class ManagerInvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlaceInvitation
        fields = (
            "id",
            "place",
            "email",
            "status",
            "accepted_by",
            "invited_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "accepted_by",
            "invited_by",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        if self.instance is not None:
            for field in ("place", "email"):
                if field in attrs and attrs[field] != getattr(self.instance, field):
                    raise serializers.ValidationError(
                        {field: "This field cannot be changed."}
                    )
        return attrs

    def validate_status(self, value: str) -> str:
        instance: PlaceInvitation | None = self.instance
        if instance is None:
            if value != PlaceInvitationStatus.PENDING:
                raise serializers.ValidationError(
                    "New invitations must start as pending."
                )
            return value
        allowed = MANAGER_ALLOWED_TRANSITIONS.get(instance.status, set())
        if value not in allowed:
            raise serializers.ValidationError(
                f"Transition from {instance.status} to {value} is not allowed."
            )
        return value
