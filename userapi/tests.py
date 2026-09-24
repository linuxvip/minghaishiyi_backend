"""微信小程序登录（T-5.2）的接口测试。

不联网：code2session 的真实实现在 `userapi.views` 里被换掉，这里只验证
「拿到 openid 之后我们怎么建号、怎么发 token、怎么处理异常」。
"""
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import UserProfile
from .views import _username_for
from .wechat import WechatError

URL = '/api/auth/wechat/'


class WechatLoginTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # 让 is_configured() 为真；真正的网络请求仍然被 code2session 的 patch 挡住
        self.settings_override = override_settings(WX_APPID='wx_test', WX_APPSECRET='secret')
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)

    def login(self, code='code-1', nickname='', session=None, error=None):
        payload = {'code': code}
        if nickname:
            payload['nickname'] = nickname
        with patch('userapi.views.code2session') as mocked:
            if error:
                mocked.side_effect = error
            else:
                mocked.return_value = session or {'openid': 'openid-A', 'unionid': None, 'session_key': 'k'}
            return self.client.post(URL, payload, format='json')

    # ---------------- 正常路径 ----------------

    def test_首次登录建档并签发与网页端同一套_token(self):
        response = self.login(nickname='张三')

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body['created'])
        self.assertIn('access', body['tokens'])
        self.assertIn('refresh', body['tokens'])
        self.assertEqual(body['user']['nickname'], '张三')

        profile = UserProfile.objects.get(openid='openid-A')
        self.assertEqual(profile.nickname, '张三')
        self.assertTrue(profile.user.is_active)
        self.assertTrue(profile.user.username.startswith('wx_'))

    def test_签发的_access_能通过鉴权接口(self):
        tokens = self.login().json()['tokens']
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        me = self.client.get('/api/auth/me/')
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()['nickname'], '微信用户')

    def test_同一个_openid_再登录不会重复建号(self):
        first = self.login()
        second = self.login(code='code-2')

        self.assertTrue(first.json()['created'])
        self.assertFalse(second.json()['created'])
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(UserProfile.objects.get(openid='openid-A').user_id, first.json()['user']['id'])

    def test_unionid_会在老账号上回填_且昵称不被覆盖(self):
        self.login(nickname='自己起的')
        response = self.login(session={'openid': 'openid-A', 'unionid': 'union-1', 'session_key': 'k'}, nickname='微信昵称')

        self.assertFalse(response.json()['created'])
        profile = UserProfile.objects.get(openid='openid-A')
        self.assertEqual(profile.unionid, 'union-1')
        self.assertEqual(profile.nickname, '自己起的')

    def test_没有昵称时给一个默认昵称(self):
        self.login()
        self.assertEqual(UserProfile.objects.get(openid='openid-A').nickname, '微信用户')

    def test_不同_openid_是两个用户(self):
        self.login(session={'openid': 'openid-A', 'unionid': None, 'session_key': ''})
        self.login(session={'openid': 'openid-B', 'unionid': None, 'session_key': ''})
        self.assertEqual(UserProfile.objects.filter(openid__isnull=False).count(), 2)

    def test_网页端老账号可以并存_多个空_openid_不撞唯一约束(self):
        for i in range(3):
            User.objects.create_user(username=f'web{i}', password='pw12345678')
            UserProfile.objects.create(user=User.objects.get(username=f'web{i}'))
        self.assertEqual(UserProfile.objects.filter(openid__isnull=True).count(), 3)

    # ---------------- 异常路径 ----------------

    def test_缺少_code_返回_400(self):
        response = self.client.post(URL, {}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('code', response.json())

    def test_微信报错时返回可读文案_不外泄_errmsg(self):
        response = self.login(error=WechatError('登录凭证已失效，请重新登录', errcode=40029))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], '登录凭证已失效，请重新登录')
        self.assertEqual(User.objects.count(), 0, '失败不该留下半个用户')

    def test_服务端没配密钥时返回_503_而不是签一个假用户(self):
        with override_settings(WX_APPID='', WX_APPSECRET=''):
            response = self.client.post(URL, {'code': 'c'}, format='json')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(User.objects.count(), 0)

    def test_被停用的账号不能登录(self):
        self.login()
        user = UserProfile.objects.get(openid='openid-A').user
        user.is_active = False
        user.save(update_fields=['is_active'])

        response = self.login()
        self.assertEqual(response.status_code, 403)

    # ---------------- 用户名生成 ----------------

    def test_用户名撞车时补随机后缀(self):
        openid = 'o' * 40
        base = 'wx_' + openid[:28]
        User.objects.create_user(username=base, password=None)

        generated = _username_for(openid)
        self.assertNotEqual(generated, base)
        self.assertTrue(generated.startswith(base[:24]))
        self.assertLessEqual(len(generated), 150)
