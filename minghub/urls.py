from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'destiny-cases', views.DestinyCaseViewSet)  # 注册命例视图集

urlpatterns = [
    path('', include(router.urls)),
]
