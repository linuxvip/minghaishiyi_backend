from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework import filters
from .models import Article
from .serializers import AdminArticleSerializer


class ArticlePagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


class AdminArticleViewSet(viewsets.ModelViewSet):
    """管理端文章 CRUD"""
    queryset = Article.objects.all()
    serializer_class = AdminArticleSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ArticlePagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'summary', 'category', 'source', 'tags']
    ordering_fields = ['id', 'title', 'sort_order', 'is_published', 'published_time', 'created_time', 'updated_time']
    ordering = ['-sort_order', '-published_time', '-created_time']
