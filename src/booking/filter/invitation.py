from django_filters import rest_framework as filters

from booking.constants.invitation import PlaceInvitationStatus
from booking.models import Place, PlaceInvitation


class MyInvitationFilter(filters.FilterSet):
    status = filters.ChoiceFilter(choices=PlaceInvitationStatus.choices)

    class Meta:
        model = PlaceInvitation
        fields = ["status"]


class ManagerInvitationFilter(filters.FilterSet):
    place = filters.ModelChoiceFilter(queryset=Place.objects.all())
    status = filters.MultipleChoiceFilter(
        field_name="status",
        choices=PlaceInvitationStatus.choices,
    )

    class Meta:
        model = PlaceInvitation
        fields = ["place", "status"]
