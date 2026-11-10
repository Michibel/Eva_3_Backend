"""
Serializers para cuentas y usuarios
"""
from rest_framework import serializers
from .models import User, Profile, AuditLog


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['avatar', 'address', 'birth_date', 'preferences', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(required=False)
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone', 'role', 'role_display', 'is_verified', 'is_active', 'date_joined', 'profile']
        read_only_fields = ['id', 'date_joined', 'role_display']

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', None)
        profile, _ = Profile.objects.get_or_create(user=instance)

        request = self.context.get('request')
        if request and request.FILES and 'avatar' in request.FILES:
            profile.avatar = request.FILES['avatar']
            profile.save()
        elif hasattr(self, 'initial_data') and isinstance(self.initial_data, dict):
            if 'avatar' in self.initial_data and self.initial_data['avatar']:
                profile.avatar = self.initial_data['avatar']
                profile.save()

        if profile_data:
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()
        return super().update(instance, validated_data)


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone', 'role', 'password', 'password_confirm']

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Las contraseñas no coinciden.'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data, password=password)
        Profile.objects.create(user=user)
        return user


class UserListSerializer(serializers.ModelSerializer):
    """Serializer ligero para listados"""
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'role_display', 'is_verified', 'is_active']


class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = AuditLog
        fields = ['id', 'action', 'model_name', 'object_id', 'changes', 'user', 'user_name', 'ip_address', 'created_at']
        read_only_fields = fields