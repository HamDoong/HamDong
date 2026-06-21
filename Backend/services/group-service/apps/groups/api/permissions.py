from rest_framework.permissions import BasePermission


class IsGroupMember(BasePermission):
    """Placeholder permission: check membership in view-level logic instead."""

    def has_permission(self, request, view):
        # actual membership checks happen in use cases / views
        return bool(getattr(request, "user", None))
