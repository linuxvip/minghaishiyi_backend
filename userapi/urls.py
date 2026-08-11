from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    RegisterView,
    LogoutView,
    MeView,
    UserConfigView,
    UserCaseViewSet,
    FavoriteViewSet,
)

urlpatterns = [
    # 认证
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='auth-login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('auth/me/', MeView.as_view(), name='auth-me'),

    # 配置喜好
    path('user/config/', UserConfigView.as_view(), name='user-config'),

    # 我的案例
    path('user/cases/', UserCaseViewSet.as_view({
        'get': 'list', 'post': 'create',
    }), name='user-case-list'),
    path('user/cases/<int:pk>/', UserCaseViewSet.as_view({
        'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy',
    }), name='user-case-detail'),

    # 收藏
    path('user/favorites/', FavoriteViewSet.as_view({
        'get': 'list', 'post': 'create',
    }), name='user-favorite-list'),
    path('user/favorites/<int:pk>/', FavoriteViewSet.as_view({
        'delete': 'destroy',
    }), name='user-favorite-detail'),
    path('user/favorites/status/', FavoriteViewSet.as_view({'get': 'status'}), name='user-favorite-status'),
    path('user/favorites/toggle/', FavoriteViewSet.as_view({'post': 'toggle'}), name='user-favorite-toggle'),
]
