from rest_framework.permissions import BasePermission


def user_can_see_place(user, place) -> bool:
    if place.public:
        return True
    if not user.is_authenticated:
        return False
    return user.has_perm("booking.can_see", place) or user.has_perm(
        "booking.manage_place", place
    )


class PlacePermission(BasePermission):
    def has_permission(self, request, view):
        if view.action in ("list", "retrieve"):
            return True
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if view.action in ("update", "partial_update", "destroy"):
            return request.user.is_authenticated and request.user.has_perm(
                "booking.manage_place", obj
            )
        if view.action == "retrieve":
            return user_can_see_place(request.user, obj)
        if view.action == "metadata":
            return True
        return False


class ResourcePermission(BasePermission):
    def has_permission(self, request, view):
        if view.action in ("list", "retrieve"):
            return True
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if view.action in ("update", "partial_update", "destroy"):
            return request.user.is_authenticated and request.user.has_perm(
                "booking.manage_place", obj.place
            )
        if view.action == "retrieve":
            return user_can_see_place(request.user, obj.place)
        if view.action == "metadata":
            return True
        return False
