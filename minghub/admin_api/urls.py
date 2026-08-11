from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    AdminLoginView,
    LogoutView,
    CurrentUserView,
    AdminDestinyCaseViewSet,
    UserViewSet,
    GroupViewSet,
    AuditLogViewSet,
    UploadView,
    SystemConfigView,
)

router = DefaultRouter()
router.register(r'destiny-cases', AdminDestinyCaseViewSet, basename='admin-destiny-case')
router.register(r'users', UserViewSet, basename='admin-user')
router.register(r'groups', GroupViewSet, basename='admin-group')
router.register(r'audit-logs', AuditLogViewSet, basename='admin-audit-log')

urlpatterns = [
    path('auth/login/', AdminLoginView.as_view(), name='admin-auth-login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='admin-auth-refresh'),
    path('auth/logout/', LogoutView.as_view(), name='admin-auth-logout'),
    path('auth/me/', CurrentUserView.as_view(), name='admin-auth-me'),
    path('upload/', UploadView.as_view(), name='admin-upload'),
    path('system-configs/', SystemConfigView.as_view(), name='admin-system-configs'),
    path('', include(router.urls)),
]
