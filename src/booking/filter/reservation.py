from django_filters import rest_framework as filters
from booking.models import Place, Reservation


class ReservationFilter(filters.FilterSet):
    resource = filters.UUIDFilter(field_name="resource", lookup_expr="exact")
    place = filters.ModelMultipleChoiceFilter(
        queryset=Place.objects.all(),
        field_name="resource__place",
    )
    overlap_start = filters.DateTimeFilter(
        field_name="ends_at", lookup_expr="gte", required=False
    )
    overlap_end = filters.DateTimeFilter(
        field_name="starts_at", lookup_expr="lte", required=False
    )

    class Meta:
        model = Reservation
        fields = ["resource", "place", "overlap_start", "overlap_end"]
