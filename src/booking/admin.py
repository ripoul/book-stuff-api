from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from booking.models import Place, Reservation, Resource


@admin.register(Place)
class PlaceAdmin(GuardedModelAdmin):
    list_display = ("name", "public", "created_at")


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ("name", "place", "created_at")
    list_filter = ("place",)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("resource", "starts_at", "ends_at", "created_by", "created_at")
    list_filter = ("resource__place",)
