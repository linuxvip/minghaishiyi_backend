from django.db import models
from django.utils import timezone


class Article(models.Model):
    title = models.CharField(max_length=255, verbose_name="文章标题")
    url = models.URLField(max_length=1000, verbose_name="文章链接")
    cover_url = models.CharField(max_length=1000, blank=True, default='', verbose_name="封面图")
    summary = models.TextField(blank=True, default='', verbose_name="文章摘要")
    category = models.CharField(max_length=100, blank=True, default='', verbose_name="分类")
    source = models.CharField(max_length=255, blank=True, default='', verbose_name="来源/作者")
    tags = models.CharField(max_length=500, blank=True, default='', verbose_name="标签(JSON)")
    sort_order = models.IntegerField(default=0, verbose_name="排序权重")
    is_published = models.BooleanField(default=True, verbose_name="是否显示")
    published_time = models.DateTimeField(blank=True, null=True, verbose_name="发布时间")
    created_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        ordering = ['-sort_order', '-published_time', '-created_time']
        verbose_name = "文章"
        verbose_name_plural = verbose_name

    def save(self, *args, **kwargs):
        if self.is_published and not self.published_time:
            self.published_time = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
