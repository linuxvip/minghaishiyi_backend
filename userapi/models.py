from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class UserProfile(models.Model):
    """用户扩展信息：昵称 + 配置喜好"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name="用户")
    nickname = models.CharField(max_length=64, blank=True, default='', verbose_name="昵称")
    preferences = models.JSONField(default=dict, blank=True, verbose_name="配置喜好")
    created_time = models.DateTimeField(auto_now_add=True, verbose_name="注册时间")
    updated_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "用户资料"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.nickname or self.user.username


class UserCase(models.Model):
    """用户自己保存的独有案例"""
    GENDER_CHOICES = (
        (1, '乾造'),
        (0, '坤造'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='my_cases', verbose_name="所属用户")
    gender = models.SmallIntegerField(choices=GENDER_CHOICES, verbose_name="性别")
    year_ganzhi = models.CharField(max_length=10, verbose_name="年柱")
    month_ganzhi = models.CharField(max_length=10, verbose_name="月柱")
    day_ganzhi = models.CharField(max_length=10, verbose_name="日柱")
    hour_ganzhi = models.CharField(max_length=10, verbose_name="时柱")
    subject_name = models.CharField(max_length=64, blank=True, default='', verbose_name="姓名")
    notes = models.TextField(blank=True, default='', verbose_name="备注")
    input_snapshot = models.JSONField(default=dict, blank=True, verbose_name="排盘输入快照")
    created_time = models.DateTimeField(auto_now_add=True, verbose_name="保存时间")
    updated_time = models.DateTimeField(auto_now=True, verbose_name="修改时间")

    class Meta:
        ordering = ["-created_time"]
        verbose_name = "我的案例"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.get_gender_display()} - {self.year_ganzhi} {self.month_ganzhi} {self.day_ganzhi} {self.hour_ganzhi}"


class Favorite(models.Model):
    """用户收藏：通用外键支持命例库案例 / 文章 / 我的案例"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites', verbose_name="所属用户")
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, verbose_name="对象类型")
    object_id = models.PositiveIntegerField(verbose_name="对象ID")
    content_object = GenericForeignKey('content_type', 'object_id')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name="收藏时间")

    class Meta:
        ordering = ["-created_time"]
        verbose_name = "收藏"
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'content_type', 'object_id'],
                name='uniq_user_favorite',
            ),
        ]

    def __str__(self):
        return f"{self.user.username} -> {self.content_type} #{self.object_id}"
