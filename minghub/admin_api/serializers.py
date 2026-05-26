from rest_framework import serializers
from django.contrib.auth.models import User, Group
from minghub.models import DestinyCase


class AdminDestinyCaseSerializer(serializers.ModelSerializer):
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
