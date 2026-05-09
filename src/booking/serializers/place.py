from rest_framework import serializers

from booking.models import Place


class PlaceSerializer(serializers.ModelSerializer):
    can_manage = serializers.SerializerMethodField()

    class Meta:
        model = Place
        fields = ("id", "name", "public", "created_at", "updated_at", "can_manage")
        read_only_fields = ("id", "created_at", "updated_at", "can_manage")

    def get_can_manage(self, obj: Place) -> bool:
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return request.user.has_perm("booking.manage_place", obj)
