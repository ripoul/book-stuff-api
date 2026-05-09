from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from booking.models import Place, Resource


@admin.register(Place)
class PlaceAdmin(GuardedModelAdmin):
    list_display = ("name", "public", "created_at")


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ("name", "place", "created_at")
    list_filter = ("place",)
