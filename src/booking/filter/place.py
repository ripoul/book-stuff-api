from django_filters import rest_framework as filters
from guardian.shortcuts import get_objects_for_user

from booking.models import Place


class PlaceFilter(filters.FilterSet):
    name = filters.CharFilter(lookup_expr="icontains")
    managed_by_me = filters.BooleanFilter(method="filter_managed_by_me")

    class Meta:
        model = Place
        fields = ["name"]

    def filter_managed_by_me(self, queryset, name, value):
        if not value:
            return queryset
        request = getattr(self, "request", None)
        if not request or not request.user.is_authenticated:
            return queryset.none()
        managed = get_objects_for_user(
            request.user,
            "booking.manage_place",
            Place,
        )
        return queryset.filter(pk__in=managed.values_list("pk", flat=True))
