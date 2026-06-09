from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    """Solo usuarios is_staff pueden usar los endpoints de administración."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class IsOwnerOrAdmin(BasePermission):
    """El usuario solo puede ver sus propios datos, o el admin ve todo."""
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj == request.user
