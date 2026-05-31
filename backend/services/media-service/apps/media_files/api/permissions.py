from rest_framework.permissions import BasePermission


class IsActiveGroupMember(BasePermission):
    def has_permission(self, request, view):
        return bool(getattr(request.user, "sub", None))


class CanManageMediaFile(BasePermission):
    def has_permission(self, request, view):
        return bool(getattr(request.user, "sub", None))
