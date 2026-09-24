"""微信小程序服务端接口。

只做一件事：拿前端 `wx.login()` 给的 code 去换 openid / unionid。
密钥一律从环境变量读（`WX_APPID` / `WX_APPSECRET`），绝不写进代码——
这个仓库是公开的，密钥一旦入库就等于公开。
"""
import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

CODE2SESSION_URL = 'https://api.weixin.qq.com/sns/jscode2session'

# 微信侧常见的错误码 → 给前端看得懂的话
ERRCODE_MESSAGES = {
    -1: '微信服务繁忙，请稍后重试',
    40029: '登录凭证已失效，请重新登录',
    45011: '登录过于频繁，请稍后重试',
    40226: '该账号被微信标记为高风险，暂时无法登录',
}


class WechatError(Exception):
    """调微信接口失败。message 可以直接回给前端。"""

    def __init__(self, message, errcode=None):
        super().__init__(message)
        self.message = message
        self.errcode = errcode


def is_configured():
    return bool(getattr(settings, 'WX_APPID', '') and getattr(settings, 'WX_APPSECRET', ''))


def code2session(code):
    """code → {'openid': ..., 'unionid': ..., 'session_key': ...}

    失败一律抛 WechatError（网络问题、微信返回错误码、返回体缺 openid 都算）。
    """
    if not is_configured():
        raise WechatError('服务端尚未配置微信密钥，请联系管理员')

    if not code:
        raise WechatError('缺少登录凭证 code')

    params = {
        'appid': settings.WX_APPID,
        'secret': settings.WX_APPSECRET,
        'js_code': code,
        'grant_type': 'authorization_code',
    }
    timeout = getattr(settings, 'WX_API_TIMEOUT', 5)

    try:
        response = httpx.get(CODE2SESSION_URL, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        logger.warning('jscode2session 请求失败: %s', exc)
        raise WechatError('无法连接微信服务器，请稍后重试') from exc
    except ValueError as exc:  # 返回体不是 JSON
        logger.warning('jscode2session 返回体无法解析')
        raise WechatError('微信返回了无法识别的响应') from exc

    errcode = data.get('errcode')
    if errcode:
        message = ERRCODE_MESSAGES.get(errcode, '微信登录失败，请重试')
        # errmsg 里可能有细节，但只写日志不外传（避免把内部信息带给前端）
        logger.warning('jscode2session 错误码 %s: %s', errcode, data.get('errmsg'))
        raise WechatError(message, errcode=errcode)

    openid = data.get('openid')
    if not openid:
        logger.warning('jscode2session 没有返回 openid')
        raise WechatError('微信没有返回用户标识')

    return {
        'openid': openid,
        'unionid': data.get('unionid') or None,
        'session_key': data.get('session_key') or '',
    }
