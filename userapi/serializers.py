from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from minghub.models import DestinyCase
from articles.models import Article
from .models import UserProfile, UserCase, Favorite


# 收藏对象类型注册表
OBJECT_TYPE_MAP = {
    'destiny_case': DestinyCase,
    'article': Article,
    'user_case': UserCase,
}
OBJECT_TYPE_CHOICES = [(k, k) for k in OBJECT_TYPE_MAP]


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(min_length=3, max_length=32)
    password = serializers.CharField(min_length=8, write_only=True)
    password2 = serializers.CharField(min_length=8, write_only=True)
    nickname = serializers.CharField(max_length=64, required=False, allow_blank=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('该用户名已被占用')
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password2': '两次输入的密码不一致'})
        return attrs

    def create(self, validated_data):
        nickname = validated_data.pop('nickname', '')
        password = validated_data.pop('password2')
        validated_data.pop('password', None)
        user = User.objects.create_user(
            username=validated_data['username'],
            password=password,
            is_active=True,
        )
        UserProfile.objects.create(user=user, nickname=nickname)
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = UserProfile
        fields = ['id', 'username', 'nickname', 'preferences', 'created_time']


class UserCaseSerializer(serializers.ModelSerializer):
    HEAVENLY_STEMS = set('甲乙丙丁戊己庚辛壬癸')
    EARTHLY_BRANCHES = set('子丑寅卯辰巳午未申酉戌亥')

    PILLAR_FIELDS = ['year_ganzhi', 'month_ganzhi', 'day_ganzhi', 'hour_ganzhi']
    PILLAR_NAMES = {
        'year_ganzhi': '年柱', 'month_ganzhi': '月柱',
        'day_ganzhi': '日柱', 'hour_ganzhi': '时柱',
    }

    def _validate_pillar(self, value, field_name):
        if not value or len(value) != 2:
            raise serializers.ValidationError(f'{self.PILLAR_NAMES[field_name]}格式应为"甲子"（2个汉字）')
        gan, zhi = value[0], value[1]
        if gan not in self.HEAVENLY_STEMS:
            raise serializers.ValidationError(f'{self.PILLAR_NAMES[field_name]}："{gan}"不是有效天干')
        if zhi not in self.EARTHLY_BRANCHES:
            raise serializers.ValidationError(f'{self.PILLAR_NAMES[field_name]}："{zhi}"不是有效地支')

    def validate_year_ganzhi(self, value):
        self._validate_pillar(value, 'year_ganzhi')
        return value

    def validate_month_ganzhi(self, value):
        self._validate_pillar(value, 'month_ganzhi')
        return value

    def validate_day_ganzhi(self, value):
        self._validate_pillar(value, 'day_ganzhi')
        return value

    def validate_hour_ganzhi(self, value):
        self._validate_pillar(value, 'hour_ganzhi')
        return value

    class Meta:
        model = UserCase
        fields = [
            'id', 'gender', 'year_ganzhi', 'month_ganzhi', 'day_ganzhi', 'hour_ganzhi',
            'subject_name', 'notes', 'input_snapshot', 'created_time', 'updated_time',
        ]
        read_only_fields = ['id', 'created_time', 'updated_time']


def build_object_summary(obj):
    """为收藏列表构造可渲染的目标摘要"""
    if isinstance(obj, DestinyCase):
        return {
            'kind': 'destiny_case',
            'id': obj.id,
            'source': obj.source,
            'gender': obj.gender,
            'year_ganzhi': obj.year_ganzhi,
            'month_ganzhi': obj.month_ganzhi,
            'day_ganzhi': obj.day_ganzhi,
            'hour_ganzhi': obj.hour_ganzhi,
            'feedback': (obj.feedback or '')[:200],
        }
    if isinstance(obj, Article):
        return {
            'kind': 'article',
            'id': obj.id,
            'title': obj.title,
            'url': obj.url,
            'cover_url': obj.cover_url,
            'summary': obj.summary,
            'source': obj.source,
            'category': obj.category,
        }
    if isinstance(obj, UserCase):
        return {
            'kind': 'user_case',
            'id': obj.id,
            'gender': obj.gender,
            'year_ganzhi': obj.year_ganzhi,
            'month_ganzhi': obj.month_ganzhi,
            'day_ganzhi': obj.day_ganzhi,
            'hour_ganzhi': obj.hour_ganzhi,
            'subject_name': obj.subject_name,
            'notes': (obj.notes or '')[:200],
        }
    return None


class FavoriteSerializer(serializers.ModelSerializer):
    object_type = serializers.ChoiceField(choices=OBJECT_TYPE_CHOICES, write_only=True)
    object_summary = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Favorite
        fields = ['id', 'object_type', 'object_id', 'object_summary', 'created_time']
        read_only_fields = ['id', 'created_time']

    def validate(self, attrs):
        object_type = attrs.get('object_type')
        object_id = attrs.get('object_id')
        model = OBJECT_TYPE_MAP.get(object_type)
        if not model:
            raise serializers.ValidationError({'object_type': '不支持的收藏类型'})
        if not model.objects.filter(id=object_id).exists():
            raise serializers.ValidationError({'object_id': '收藏对象不存在'})
        return attrs

    def get_object_summary(self, obj):
        return build_object_summary(obj.content_object)

    def create(self, validated_data):
        object_type = validated_data.pop('object_type')
        object_id = validated_data.pop('object_id')
        model = OBJECT_TYPE_MAP[object_type]
        validated_data['content_type'] = ContentType.objects.get_for_model(model)
        validated_data['object_id'] = object_id
        favorite, created = Favorite.objects.get_or_create(
            user=validated_data['user'],
            content_type=validated_data['content_type'],
            object_id=object_id,
            defaults=validated_data,
        )
        return favorite
