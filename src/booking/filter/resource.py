from django_filters import rest_framework as filters

from booking.models import Place, Resource


class ResourceFilter(filters.FilterSet):
    name = filters.CharFilter(lookup_expr="icontains")
    place = filters.ModelMultipleChoiceFilter(
        queryset=Place.objects.all(),
        field_name="place",
    )

    class Meta:
        model = Resource
        fields = ["name"]
