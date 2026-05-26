from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    LogoutView,
    CurrentUserView,
    AdminDestinyCaseViewSet,
    UserViewSet,
    GroupViewSet,
)

router = DefaultRouter()
router.register(r'destiny-cases', AdminDestinyCaseViewSet, basename='admin-destiny-case')
router.register(r'users', UserViewSet, basename='admin-user')
router.register(r'groups', GroupViewSet, basename='admin-group')

urlpatterns = [
    path('auth/login/', TokenObtainPairView.as_view(), name='admin-auth-login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='admin-auth-refresh'),
    path('auth/logout/', LogoutView.as_view(), name='admin-auth-logout'),
    path('auth/me/', CurrentUserView.as_view(), name='admin-auth-me'),
    path('', include(router.urls)),
]
