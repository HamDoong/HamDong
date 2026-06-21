from rest_framework.permissions import BasePermission


class IsAuthenticatedSettlementUser(BasePermission):
    def has_permission(self, request, view):
        return bool(getattr(request.user, "sub", None))


class IsActiveGroupMember(BasePermission):
    def has_permission(self, request, view):
        return bool(getattr(request.user, "sub", None))


class CanManageSettlement(BasePermission):
    def has_permission(self, request, view):
        return bool(getattr(request.user, "sub", None))
