from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'destiny-cases', views.DestinyCaseViewSet)

urlpatterns = [
    path('system-configs/', views.PublicConfigView.as_view(), name='public-system-configs'),
    path('', include(router.urls)),
]
