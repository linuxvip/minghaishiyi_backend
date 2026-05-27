from rest_framework import serializers
from .models import Article


class ArticleSerializer(serializers.ModelSerializer):
    """公开只读序列化器：前台展示用"""

    class Meta:
        model = Article
        fields = [
            'id', 'title', 'url', 'cover_url', 'summary',
            'category', 'source', 'tags', 'published_time',
        ]


class AdminArticleSerializer(serializers.ModelSerializer):
    """管理端全字段序列化器"""

    class Meta:
        model = Article
        fields = '__all__'
        read_only_fields = ['id', 'published_time', 'created_time', 'updated_time']
