"""自定义异常处理模块"""

from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404


def custom_exception_handler(exc, context):
    """
    自定义异常处理函数，专门处理404错误
    其他错误使用DRF默认处理
    """
    # 检查是否是404错误
    if isinstance(exc, Http404):
        return Response(
            {
                'status': 'error',
                'code': 'not_found',
                'message': '请求的资源不存在'
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    # 其他错误使用DRF默认处理
    return drf_exception_handler(exc, context)