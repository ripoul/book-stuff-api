from django.db import models


class Place(models.Model):
    name = models.CharField(max_length=255)
    public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = [
            ("manage_place", "Can manage place"),
            ("can_see", "Can see place"),
        ]

    def __str__(self) -> str:
        return self.name
