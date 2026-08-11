from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from .models import UserProfile, UserCase, Favorite
from .serializers import (
    RegisterSerializer,
    UserProfileSerializer,
    UserCaseSerializer,
    FavoriteSerializer,
    OBJECT_TYPE_MAP,
)


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
