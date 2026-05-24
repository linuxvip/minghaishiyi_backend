from rest_framework import serializers, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework import filters
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import AllowAny
from drf_yasg.utils import swagger_auto_schema
from django_filters import FilterSet, CharFilter
from django.db.models import Count, Q
from django.db.models.expressions import RawSQL
from .models import DestinyCase
from rest_framework.response import Response
from rest_framework import mixins


class DestinyCaseFilter(FilterSet):
    """命例数据过滤器，支持四柱模糊搜索和 label JSON 内字段精确筛选"""
    year_ganzhi = CharFilter(lookup_expr='icontains')
    month_ganzhi = CharFilter(lookup_expr='icontains')
    day_ganzhi = CharFilter(lookup_expr='icontains')
    hour_ganzhi = CharFilter(lookup_expr='icontains')
    source = CharFilter(field_name='source', lookup_expr='exact')
    label = CharFilter(lookup_expr='icontains')

    # label JSON 内部字段筛选（数据库层 JSON_EXTRACT，避免全表扫描）
    chusheng = CharFilter(method='filter_label_json')
    xueli = CharFilter(method='filter_label_json')
    zhiye_leibie = CharFilter(method='filter_label_json')
    hunyin_zhuangtai = CharFilter(method='filter_label_json')
    caifu_cengci = CharFilter(method='filter_label_json')

    LABEL_JSON_PATHS = {
        'chusheng': '$."出身"',
        'xueli': '$."学历"',
        'zhiye_leibie': '$."职业类别"',
        'hunyin_zhuangtai': '$."婚姻状态"',
        'caifu_cengci': '$."财富层次"',
    }

    def filter_label_json(self, queryset, name, value):
        json_path = self.LABEL_JSON_PATHS.get(name)
        if not json_path or not value:
            return queryset
        return queryset.exclude(
            Q(label='') | Q(label__isnull=True)
        ).annotate(
            **{f'_label_{name}': RawSQL(
                "JSON_UNQUOTE(JSON_EXTRACT(label, %s))",
                (json_path,)
            )}
        ).filter(**{f'_label_{name}': value})

    class Meta:
        model = DestinyCase
        fields = [
            'gender', 'source', 'year_ganzhi', 'month_ganzhi', 'day_ganzhi',
            'hour_ganzhi', 'label',
            'chusheng', 'xueli', 'zhiye_leibie', 'hunyin_zhuangtai', 'caifu_cengci',
        ]


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


@swagger_auto_schema(tags=['命例数据'], operation_description='获取命例数据列表，支持分页、过滤和搜索',)
class DestinyCaseViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin, 
    mixins.RetrieveModelMixin, 
    viewsets.GenericViewSet):
    """命例数据视图集，仅提供只读功能"""
    
    queryset = DestinyCase.objects.all()  # 获取所有命例数据
    serializer_class = DestinyCaseSerializer  # 使用上面定义的序列化器
    pagination_class = DestinyCasePagination  # 启用分页功能
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    permission_classes = [AllowAny]  # 允许所有用户访问
    
    # 使用自定义过滤器（支持模糊搜索和 label JSON 筛选）
    filterset_class = DestinyCaseFilter

    @swagger_auto_schema(
        operation_description='获取所有可用来源列表，去重、去空、按数量降序排列',
        responses={200: '{"sources": ["source1", "source2", ...]}'},
    )
    @action(detail=False, methods=['get'], url_path='sources')
    def sources(self, request):
        sources = (
            DestinyCase.objects
            .exclude(Q(source='') | Q(source__isnull=True))
            .values('source')
            .annotate(count=Count('source'))
            .order_by('-count')
            .values_list('source', flat=True)
        )
        return Response({"sources": list(sources)})

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

    @swagger_auto_schema(
        operation_description='新增命例数据记录（需要passwd参数）',
        request_body=DestinyCaseSerializer,
        responses={
            201: DestinyCaseSerializer,
            400: "参数错误",
            401: "密码错误"
        },
    )
    def create(self, request, *args, **kwargs):
        password = request.data.get('passwd', '')
        if password != 'minghaishiyi':
            return Response({"error": "密码错误"}, status=401)
        return super().create(request, *args, **kwargs)
