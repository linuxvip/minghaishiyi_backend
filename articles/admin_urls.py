from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .admin_views import AdminArticleViewSet

router = DefaultRouter()
router.register(r'', AdminArticleViewSet, basename='admin-article')

urlpatterns = [
    path('', include(router.urls)),
]
