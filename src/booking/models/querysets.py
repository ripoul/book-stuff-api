from django.db import models
from guardian.shortcuts import get_objects_for_user


class PlaceQuerySet(models.QuerySet):
    def visible_for(self, user):
        public = self.filter(public=True)
        if not getattr(user, "is_authenticated", False):
            return public
        private = get_objects_for_user(
            user,
            ["booking.can_see", "booking.manage_place"],
            self.model,
            any_perm=True,
        )
        return (public | private).distinct()


class ResourceQuerySet(models.QuerySet):
    def visible_for(self, user):
        from booking.models.place import Place

        return self.filter(place__in=Place.objects.visible_for(user)).select_related(
            "place"
        )


class PlaceManager(models.Manager):
    def get_queryset(self) -> PlaceQuerySet:
        return PlaceQuerySet(self.model, using=self._db)

    def visible_for(self, user):
        return self.get_queryset().visible_for(user)


class ResourceManager(models.Manager):
    def get_queryset(self) -> ResourceQuerySet:
        return ResourceQuerySet(self.model, using=self._db)

    def visible_for(self, user):
        return self.get_queryset().visible_for(user)
