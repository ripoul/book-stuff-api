from django.db import models

from booking.models.base import UUIDPrimaryKeyModel
from booking.models.place import Place


class Resource(UUIDPrimaryKeyModel):
    place = models.ForeignKey(
        Place,
        on_delete=models.CASCADE,
        related_name="resources",
    )
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name
