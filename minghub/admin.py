from django.contrib import admin
from .models import DestinyCase


@admin.register(DestinyCase)
class DestinyCaseAdmin(admin.ModelAdmin):
    """命例模型的管理界面配置"""
    # 列表显示的字段
    list_display = (
        'id', 'source', 'gender', 'year_ganzhi', 'month_ganzhi', 'day_ganzhi', 
        'hour_ganzhi', 'label',
    )
    
    # 搜索字段
    search_fields = (
        'source', 'year_ganzhi', 'month_ganzhi', 'day_ganzhi', 'hour_ganzhi', 'label'
    )
    
    # 过滤字段
    list_filter = (
        'gender', 
        'source',
        'year_ganzhi',
        'month_ganzhi',
    )
    
    # 默认排序
    ordering = ('-created_time',)
    
    # 日期分层导航
    # date_hierarchy = 'created_time'
    
    # 列表页可编辑字段
    # list_editable = ('feedback', 'label')
    
    # 每页显示记录数
    list_per_page = 20
    
    # 详细页字段分组
    fieldsets = (
        (
            '命例基本信息', {
                'fields': ('source', 'gender')
            }
        ),
        (
            '八字信息', {
                'fields': ('year_ganzhi', 'month_ganzhi', 'day_ganzhi', 'hour_ganzhi')
            }
        ),
        (
            '附加信息', {
                'fields': ('feedback', 'original_url', 'label')
            }
        ),
    )
