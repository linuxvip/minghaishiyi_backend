from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from .models import Article
from .serializers import ArticleSerializer


class ArticleListView(ListAPIView):
    """公开接口：前台展示文章列表，仅返回已发布的文章"""
    queryset = Article.objects.filter(is_published=True)
    serializer_class = ArticleSerializer
    permission_classes = [AllowAny]
    pagination_class = None  # 前台不分页，一次性返回所有已发布文章
