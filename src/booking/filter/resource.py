from django_filters import rest_framework as filters

from booking.models import Resource


class ResourceFilter(filters.FilterSet):
    name = filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Resource
        fields = ["name"]
