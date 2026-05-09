from rest_framework import serializers

from booking.models import Place


class PlaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Place
        fields = ("id", "name", "public", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")
