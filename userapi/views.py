from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction
from drf_yasg.utils import swagger_auto_schema
import secrets

from .models import UserProfile, UserCase, Favorite
from .serializers import (
    RegisterSerializer,
    WechatLoginSerializer,
    UserProfileSerializer,
    UserCaseSerializer,
    FavoriteSerializer,
    OBJECT_TYPE_MAP,
)
from .wechat import WechatError, code2session, is_configured


def _username_for(openid):
    """openid → 一个合法且不冲突的 Django 用户名"""
    base = 'wx_' + openid[:28]
    if not User.objects.filter(username=base).exists():
        return base
    for _ in range(5):
        candidate = f'{base[:24]}_{secrets.token_hex(3)}'
        if not User.objects.filter(username=candidate).exists():
            return candidate
    return 'wx_' + secrets.token_hex(16)


def _issue_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        profile, _ = UserProfile.objects.get_or_create(user=user)
        return Response({
            'tokens': _issue_tokens(user),
            'user': UserProfileSerializer(profile).data,
        }, status=status.HTTP_201_CREATED)


class WechatLoginView(APIView):
    """POST /api/auth/wechat/ —— 小程序 wx.login() 的 code 换 JWT（T-5.2）

    流程：code → jscode2session → openid → 找到或创建用户 → 签发与网页端同一套 JWT。
    两边共用同一批用户数据，所以网页端登录过的账号（如果绑过微信）在小程序里是同一个。

    关于 username：微信不给用户名，但 Django 的 User 必须有。这里用 `wx_<openid 前 28 位>`
    生成，撞车时补随机后缀——openid 本身唯一，所以撞车只可能来自人为占位。
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=['认证'],
        operation_description='微信小程序登录：用 wx.login() 的 code 换 JWT',
        request_body=WechatLoginSerializer,
        responses={200: '登录成功', 400: 'code 无效 / 微信接口报错', 503: '服务端未配置微信密钥'},
    )
    def post(self, request):
        if not is_configured():
            return Response(
                {'error': '服务端尚未配置微信登录，请稍后再试'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        serializer = WechatLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data['code']
        nickname = serializer.validated_data.get('nickname', '')

        try:
            session = code2session(code)
        except WechatError as exc:
            return Response({'error': exc.message}, status=status.HTTP_400_BAD_REQUEST)

        profile = UserProfile.objects.filter(openid=session['openid']).first()
        if profile is not None and not profile.user.is_active:
            return Response({'error': '该账号已被停用'}, status=status.HTTP_403_FORBIDDEN)

        created = False
        if profile is None:
            profile = self._create_profile(session, nickname)
            created = True
        else:
            self._fill_missing(profile, session, nickname)

        return Response({
            'tokens': _issue_tokens(profile.user),
            'user': UserProfileSerializer(profile).data,
            'created': created,
        })

    @staticmethod
    def _create_profile(session, nickname):
        """建号。openid 上的唯一约束兜住并发重复登录：撞了就回头查已有的那条。"""
        openid = session['openid']
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=_username_for(openid),
                    # 微信用户没有密码：写一个不可用的，保证密码登录这条路是关着的
                    password=None,
                    is_active=True,
                )
                return UserProfile.objects.create(
                    user=user,
                    nickname=nickname or '微信用户',
                    openid=openid,
                    unionid=session.get('unionid'),
                )
        except IntegrityError:
            profile = UserProfile.objects.filter(openid=openid).first()
            if profile is None:
                raise
            return profile

    @staticmethod
    def _fill_missing(profile, session, nickname):
        """老账号补 unionid；昵称只在用户自己没设过的时候才用微信给的兜底"""
        updates = []
        if session.get('unionid') and not profile.unionid:
            profile.unionid = session['unionid']
            updates.append('unionid')
        if nickname and not profile.nickname:
            profile.nickname = nickname
            updates.append('nickname')
        if updates:
            profile.save(update_fields=updates + ['updated_time'])


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            token = RefreshToken(request.data.get('refresh'))
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return Response(UserProfileSerializer(profile).data)

    def put(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class UserConfigView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return Response(profile.preferences)

    def put(self, request):
        preferences = request.data or {}
        if not isinstance(preferences, dict):
            return Response({'error': '配置必须为 JSON 对象'}, status=status.HTTP_400_BAD_REQUEST)
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.preferences = preferences
        profile.save(update_fields=['preferences', 'updated_time'])
        return Response(profile.preferences)


class UserCaseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UserCaseSerializer

    def get_queryset(self):
        return UserCase.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        v = serializer.validated_data
        lookup = {
            'gender': v.get('gender'),
            'year_ganzhi': v.get('year_ganzhi'),
            'month_ganzhi': v.get('month_ganzhi'),
            'day_ganzhi': v.get('day_ganzhi'),
            'hour_ganzhi': v.get('hour_ganzhi'),
        }
        existing = UserCase.objects.filter(user=request.user, **lookup).first()
        if existing:
            for field in ('subject_name', 'notes', 'input_snapshot'):
                if field in v:
                    setattr(existing, field, v[field])
            existing.save()
            data = self.get_serializer(existing).data
            data['created'] = False
            return Response(data, status=status.HTTP_200_OK)
        user_case = serializer.save(user=request.user)
        data = self.get_serializer(user_case).data
        data['created'] = True
        return Response(data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class FavoriteViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = FavoriteSerializer

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user).select_related('content_type')

    def list(self, request):
        object_type = request.query_params.get('object_type')
        queryset = self.get_queryset()
        if object_type:
            model = OBJECT_TYPE_MAP.get(object_type)
            if not model:
                return Response({'error': '不支持的收藏类型'}, status=status.HTTP_400_BAD_REQUEST)
            ct = ContentType.objects.get_for_model(model)
            queryset = queryset.filter(content_type=ct)
        page = self.paginate_queryset(queryset) if hasattr(self, 'paginate_queryset') else None
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        favorite = serializer.save(user=request.user)
        out = self.get_serializer(favorite).data
        return Response(out, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk=None):
        favorite = self.get_queryset().filter(id=pk).first()
        if not favorite:
            return Response({'error': '收藏不存在'}, status=status.HTTP_404_NOT_FOUND)
        favorite.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def status(self, request):
        object_type = request.query_params.get('object_type')
        object_id = request.query_params.get('object_id')
        model = OBJECT_TYPE_MAP.get(object_type)
        if not model or not object_id:
            return Response({'error': '缺少 object_type / object_id'}, status=status.HTTP_400_BAD_REQUEST)
        ct = ContentType.objects.get_for_model(model)
        favorite = self.get_queryset().filter(content_type=ct, object_id=int(object_id)).first()
        return Response({'favorited': bool(favorite), 'id': favorite.id if favorite else None})

    @action(detail=False, methods=['post'])
    def toggle(self, request):
        object_type = request.data.get('object_type')
        object_id = request.data.get('object_id')
        model = OBJECT_TYPE_MAP.get(object_type)
        if not model or not object_id:
            return Response({'error': '缺少 object_type / object_id'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            object_id = int(object_id)
        except (TypeError, ValueError):
            return Response({'error': 'object_id 非法'}, status=status.HTTP_400_BAD_REQUEST)
        if not model.objects.filter(id=object_id).exists():
            return Response({'error': '收藏对象不存在'}, status=status.HTTP_404_NOT_FOUND)
        ct = ContentType.objects.get_for_model(model)
        favorite = self.get_queryset().filter(content_type=ct, object_id=object_id).first()
        if favorite:
            favorite.delete()
            return Response({'favorited': False, 'id': None})
        favorite = Favorite.objects.create(user=request.user, content_type=ct, object_id=object_id)
        return Response({'favorited': True, 'id': favorite.id})
