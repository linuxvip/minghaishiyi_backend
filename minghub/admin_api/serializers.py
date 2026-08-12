from rest_framework import serializers
from django.contrib.auth.models import User, Group
from django_filters import rest_framework as drf_filters
from minghub.models import DestinyCase, ProcessingTask


class AdminDestinyCaseSerializer(serializers.ModelSerializer):
    HEAVENLY_STEMS = set('甲乙丙丁戊己庚辛壬癸')
    EARTHLY_BRANCHES = set('子丑寅卯辰巳午未申酉戌亥')

    PILLAR_FIELDS = ['year_ganzhi', 'month_ganzhi', 'day_ganzhi', 'hour_ganzhi']
    PILLAR_NAMES = {
        'year_ganzhi': '年柱', 'month_ganzhi': '月柱',
        'day_ganzhi': '日柱', 'hour_ganzhi': '时柱',
    }

    def _validate_pillar(self, value, field_name):
        if not value or len(value) != 2:
            raise serializers.ValidationError(
                f'{self.PILLAR_NAMES[field_name]}格式应为"甲子"（2个汉字）'
            )
        gan, zhi = value[0], value[1]
        if gan not in self.HEAVENLY_STEMS:
            raise serializers.ValidationError(
                f'{self.PILLAR_NAMES[field_name]}："{gan}"不是有效天干'
            )
        if zhi not in self.EARTHLY_BRANCHES:
            raise serializers.ValidationError(
                f'{self.PILLAR_NAMES[field_name]}："{zhi}"不是有效地支'
            )

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
        model = DestinyCase
        fields = '__all__'
        read_only_fields = ['id', 'created_time', 'updated_time']


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    groups = serializers.PrimaryKeyRelatedField(many=True, queryset=Group.objects.all(), required=False)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_active', 'is_staff', 'is_superuser', 'date_joined',
            'last_login', 'groups', 'password',
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']

    def validate(self, attrs):
        if self.instance is None and not attrs.get('password'):
            raise serializers.ValidationError({'password': '创建用户时密码为必填项'})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        groups = validated_data.pop('groups', [])
        user = User.objects.create(**validated_data)
        if password:
            user.set_password(password)
        if groups:
            user.groups.set(groups)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        groups = validated_data.pop('groups', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        if groups is not None:
            instance.groups.set(groups)
        instance.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    password = serializers.CharField(min_length=8, write_only=True)


class GroupSerializer(serializers.ModelSerializer):
    user_set = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Group
        fields = ['id', 'name', 'permissions', 'user_set']


class ProcessingTaskFilter(drf_filters.FilterSet):
    status = drf_filters.ChoiceFilter(choices=ProcessingTask.STATUS_CHOICES)

    class Meta:
        model = ProcessingTask
        fields = ['status']


class ProcessingTaskSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ProcessingTask
        fields = '__all__'
        read_only_fields = ['id', 'status', 'log', 'cases_created', 'error_message',
                            'created_at', 'updated_at', 'status_display']

    def validate_url(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("链接不能为空")
        return value.strip()

    def validate_source_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("来源标签不能为空")
        return value.strip()
