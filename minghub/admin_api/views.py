from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework_simplejwt.tokens import RefreshToken
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.contrib.auth.models import User, Group

from minghub.models import DestinyCase
from minghub.views import DestinyCaseFilter, DestinyCasePagination
from .serializers import (
    AdminDestinyCaseSerializer,
    UserSerializer,
    ChangePasswordSerializer,
    GroupSerializer,
)
from .permissions import IsSuperUser


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            token = RefreshToken(request.data.get('refresh'))
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class AdminDestinyCaseViewSet(viewsets.ModelViewSet):
    queryset = DestinyCase.objects.all()
    serializer_class = AdminDestinyCaseSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = DestinyCaseFilter
    search_fields = ['source', 'year_ganzhi', 'month_ganzhi', 'day_ganzhi',
                     'hour_ganzhi', 'feedback', 'label']
    ordering_fields = ['id', 'source', 'created_time', 'updated_time']
    ordering = ['-created_time']
    pagination_class = DestinyCasePagination


class StandardPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().prefetch_related('groups', 'user_permissions')
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsSuperUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['username', 'email']
    ordering_fields = ['id', 'username', 'date_joined', 'last_login']
    ordering = ['-date_joined']
    pagination_class = StandardPagination

    @action(detail=True, methods=['post'], url_path='set-password')
    def set_password(self, request, pk=None):
        user = self.get_object()
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data['password'])
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user == request.user:
            return Response(
                {'detail': '不能删除自己的账户'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all().prefetch_related('permissions')
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated, IsSuperUser]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']
    pagination_class = StandardPagination
