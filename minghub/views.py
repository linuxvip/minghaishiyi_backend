from rest_framework import serializers, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import AllowAny
from drf_yasg.utils import swagger_auto_schema
from django_filters import FilterSet, CharFilter
from .models import DestinyCase


class DestinyCaseFilter(FilterSet):
    """命例数据过滤器，支持模糊搜索"""
    year_ganzhi = CharFilter(lookup_expr='icontains')
    month_ganzhi = CharFilter(lookup_expr='icontains')
    day_ganzhi = CharFilter(lookup_expr='icontains')
    hour_ganzhi = CharFilter(lookup_expr='icontains')
    source = CharFilter(lookup_expr='icontains')
    label = CharFilter(lookup_expr='icontains')
    
    class Meta:
        model = DestinyCase
        fields = ['gender', 'year_ganzhi', 'month_ganzhi', 'day_ganzhi', 'hour_ganzhi', 'source', 'label']


class DestinyCaseSerializer(serializers.ModelSerializer):
    """命例数据序列化器"""
    
    class Meta:
        model = DestinyCase
        """序列化器元数据"""
        model = DestinyCase
        # 显式列出需要序列化的字段，排除created_time、updated_time和original_url
        fields = [
            'id', 'source', 'gender', 'year_ganzhi', 'month_ganzhi', 
            'day_ganzhi', 'hour_ganzhi', 'feedback', 'label'
        ]


class DestinyCasePagination(PageNumberPagination):
    """命例数据分页配置"""
    page_size = 20  # 默认每页显示20条记录
    page_size_query_param = 'page_size'  # 允许客户端通过page_size参数自定义每页显示数量
    max_page_size = 100  # 最大每页显示100条记录


@swagger_auto_schema(
    tags=['命例数据'],
    operation_description='获取命例数据列表，支持分页、过滤和搜索',
)
class DestinyCaseViewSet(viewsets.ReadOnlyModelViewSet):
    """命例数据视图集，仅提供只读功能"""
    
    queryset = DestinyCase.objects.all()  # 获取所有命例数据
    serializer_class = DestinyCaseSerializer  # 使用上面定义的序列化器
    pagination_class = DestinyCasePagination  # 启用分页功能
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    permission_classes = [AllowAny]  # 允许所有用户访问
    
    # 使用自定义过滤器（支持模糊搜索）
    filterset_class = DestinyCaseFilter
    
    @swagger_auto_schema(
        operation_description='获取特定命例数据的详细信息',
        responses={200: DestinyCaseSerializer(many=False)},  # 成功响应示例
    )
    def retrieve(self, request, *args, **kwargs):
        """获取单个命例数据"""
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description='获取命例数据列表，支持分页、过滤和搜索',
        responses={200: DestinyCaseSerializer(many=True)},  # 成功响应示例
    )
    def list(self, request, *args, **kwargs):
        """获取命例数据列表"""
        return super().list(request, *args, **kwargs)

