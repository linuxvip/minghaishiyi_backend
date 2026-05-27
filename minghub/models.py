from django.db import models

# Create your models here.

class DestinyCase(models.Model):
    objects = models.Manager()

    GENDER_CHOICES = (
        (1, '乾造'),
        (0, '坤造'),
    )

    source = models.CharField(max_length=255, verbose_name="命例来源")
    gender = models.SmallIntegerField(choices=GENDER_CHOICES, verbose_name="性别")
    year_ganzhi = models.CharField(max_length=10, verbose_name="年柱")
    month_ganzhi = models.CharField(max_length=10, verbose_name="月柱")
    day_ganzhi = models.CharField(max_length=10, verbose_name="日柱")
    hour_ganzhi = models.CharField(max_length=10, verbose_name="时柱")
    feedback = models.TextField(verbose_name="命例反馈", blank=True, null=True)
    original_url = models.URLField(verbose_name="命例原网页地址", blank=True, null=True)
    label = models.CharField(max_length=255, verbose_name="命例标签", blank=True, null=True)
    created_time = models.DateTimeField(auto_now_add=True, verbose_name="添加时间")
    updated_time = models.DateTimeField(auto_now=True, verbose_name="修改时间")

    class Meta:
        ordering = ["id"]
        verbose_name = "命例"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.gender} - {self.year_ganzhi} {self.month_ganzhi} {self.day_ganzhi} {self.hour_ganzhi}"

class AuditLog(models.Model):
    ACTION_CHOICES = (
        ('CREATE', '创建'),
        ('UPDATE', '修改'),
        ('DELETE', '删除'),
    )

    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, verbose_name="操作人")
    action = models.CharField(max_length=10, choices=ACTION_CHOICES, verbose_name="操作类型")
    model_name = models.CharField(max_length=50, verbose_name="模型名称")
    object_id = models.IntegerField(verbose_name="对象ID")
    changes = models.TextField(blank=True, default='', verbose_name="变更内容")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="操作时间")

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "操作日志"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"[{self.get_action_display()}] {self.model_name}#{self.object_id} by {self.user}"

class SystemConfig(models.Model):
    key = models.CharField(max_length=100, unique=True, verbose_name='配置键')
    value = models.TextField(blank=True, default='', verbose_name='配置值')
    description = models.CharField(max_length=255, blank=True, default='', verbose_name='说明')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '系统配置'
        verbose_name_plural = verbose_name
    def __str__(self):
        return f'{self.key}: {self.value[:50]}'
