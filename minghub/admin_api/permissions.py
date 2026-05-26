from rest_framework.permissions import BasePermission


class IsSuperUser(BasePermission):
    """仅允许超级用户访问"""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_superuser
