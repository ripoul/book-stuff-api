from rest_framework.permissions import BasePermission


def resource_id_visible_for_user(user, resource_id) -> bool:
    if resource_id is None:
        return True
    from booking.models import Resource

    return Resource.objects.visible_for(user).filter(pk=resource_id).exists()


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


class ReservationPermission(BasePermission):
    def has_permission(self, request, view):
        if view.action in ("list", "retrieve"):
            return True
        if not request.user.is_authenticated:
            return False
        if view.action == "create":
            return resource_id_visible_for_user(
                request.user, request.data.get("resource")
            )
        return True

    def has_object_permission(self, request, view, obj):
        if view.action in ("update", "partial_update", "destroy"):
            if not request.user.is_authenticated:
                return False
            if "resource" in request.data and request.data.get("resource") is not None:
                new_rid = request.data.get("resource")
                if str(new_rid) != str(obj.resource_id):
                    if not resource_id_visible_for_user(request.user, new_rid):
                        return False
            if request.user.has_perm("booking.manage_place", obj.resource.place):
                return True
            return obj.created_by_id == request.user.id
        if view.action == "retrieve":
            return user_can_see_place(request.user, obj.resource.place)
        if view.action == "metadata":
            return True
        return False


class MyInvitationPermission(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        user_email = (request.user.email or "").lower()
        if not user_email:
            return False
        return obj.email.lower() == user_email


class ManagerInvitationPermission(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return request.user.is_authenticated and request.user.has_perm(
            "booking.manage_place", obj.place
        )
