from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.pagination import PageNumberPagination
from rest_framework_simplejwt.tokens import RefreshToken
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.contrib.auth.models import User, Group
from django.contrib.auth import authenticate

import csv
from django.http import HttpResponse
import json
import json
from rest_framework import serializers as drf_serializers
from django.core.cache import cache
from minghub.views import CONFIG_CACHE_KEY
from minghub.models import DestinyCase, AuditLog, SystemConfig
from minghub.views import DestinyCaseFilter, DestinyCasePagination
from .serializers import (
    AdminDestinyCaseSerializer,
    UserSerializer,
    ChangePasswordSerializer,
    GroupSerializer,
)
from .permissions import IsSuperUser


class AdminLoginView(APIView):
    """后台登录：仅允许超级管理员"""
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '')
        user = authenticate(username=username, password=password)
        if not user:
            return Response({'detail': '用户名或密码错误'}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.is_active:
            return Response({'detail': '账号已被禁用'}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.is_superuser:
            return Response({'detail': '无后台管理权限'}, status=status.HTTP_403_FORBIDDEN)
        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })


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
    permission_classes = [IsAuthenticated, IsSuperUser]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class AdminDestinyCaseViewSet(viewsets.ModelViewSet):
    queryset = DestinyCase.objects.all()
    serializer_class = AdminDestinyCaseSerializer
    permission_classes = [IsAuthenticated, IsSuperUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = DestinyCaseFilter
    search_fields = ['source', 'year_ganzhi', 'month_ganzhi', 'day_ganzhi',
                     'hour_ganzhi', 'feedback', 'label']
    ordering_fields = ['id', 'source', 'created_time', 'updated_time']
    ordering = ['-created_time']
    pagination_class = DestinyCasePagination

    @action(detail=False, methods=['get'], url_path='export-csv')
    def export_csv(self, request):
        queryset = self.filter_queryset(self.get_queryset())

        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename="minghaishiyi-cases.csv"'
        response.write('\ufeff')

        writer = csv.writer(response)
        writer.writerow([
            'ID', '来源', '性别', '年柱', '月柱', '日柱', '时柱',
            '反馈', '原文链接', '标签', '添加时间', '修改时间'
        ])

        for case in queryset.iterator(chunk_size=1000):
            writer.writerow([
                case.id,
                case.source,
                '男' if case.gender == 1 else '女',
                case.year_ganzhi,
                case.month_ganzhi,
                case.day_ganzhi,
                case.hour_ganzhi,
                case.feedback or '',
                case.original_url or '',
                case.label or '',
                case.created_time.strftime('%Y-%m-%d %H:%M:%S') if case.created_time else '',
                case.updated_time.strftime('%Y-%m-%d %H:%M:%S') if case.updated_time else '',
            ])

        return response

        return response


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


class UploadView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]

    def post(self, request):
        f = request.FILES.get("file")
        if not f: return Response({"error":"no file"}, status=400)
        import os
        d = os.path.join("/app/uploads", f.name)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        with open(d, "wb+") as dest:
            for chunk in f.chunks():
                dest.write(chunk)
        return Response({"url": "/data/" + f.name})

class SystemConfigView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUser]

    def get(self, request):
        configs = {c.key: c.value for c in SystemConfig.objects.all()}
        defaults = {"site_name": "命海拾遗", "site_subtitle": "探索八字玄机 · 洞悉人生运势", "footer_text": "Ming Hai Shi Yi · 命海拾遗", "qrcode_url": "/qrcode.jpg", "avatar_url": "/avatar.jpg", "wx_qrcode_url": "/wx_qrcode.jpg"}
        for k, v in defaults.items():
            if k not in configs:
                configs[k] = v
        return Response(configs)

    def put(self, request):
        for key, value in request.data.items():
            SystemConfig.objects.update_or_create(key=key, defaults={"value": str(value)})
        cache.delete(CONFIG_CACHE_KEY)
        return Response({"status": "ok"})


class AuditLogSerializer(drf_serializers.ModelSerializer):
    user_name = drf_serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = AuditLog
        fields = ['id', 'user', 'user_name', 'action', 'model_name', 'object_id', 'changes', 'timestamp']


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related('user').all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsSuperUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['user__username', 'model_name', 'changes']
    ordering_fields = ['id', 'timestamp', 'action']
    ordering = ['-timestamp']
    pagination_class = StandardPagination
