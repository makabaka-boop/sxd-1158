from rest_framework import serializers
from django.contrib.auth.models import User
from devices.models import (
    UserProfile, Area, Device, DeviceRecord,
    DeviceStatus, RecordType, Role,
)


class UserProfileSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = UserProfile
        fields = ['role', 'role_display']


class UserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source='profile.role', default='')
    role_display = serializers.CharField(source='profile.get_role_display', default='', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'role_display']

    def create(self, validated_data):
        profile_data = validated_data.pop('profile', {})
        password = self.context['request'].data.get('password', '123456')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=password,
        )
        UserProfile.objects.create(user=user, **profile_data)
        return user

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})
        instance.username = validated_data.get('username', instance.username)
        instance.email = validated_data.get('email', instance.email)
        instance.save()
        if profile_data:
            profile = instance.profile
            profile.role = profile_data.get('role', profile.role)
            profile.save()
        return instance


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class AreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Area
        fields = ['id', 'name']


class DeviceListSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    area_name = serializers.CharField(source='area.name', default='', read_only=True)
    responsible_person_name = serializers.CharField(
        source='responsible_person.username', default='', read_only=True
    )

    class Meta:
        model = Device
        fields = [
            'id', 'category', 'category_display', 'code', 'name',
            'area', 'area_name', 'responsible_person', 'responsible_person_name',
            'inspection_cycle_days', 'status', 'status_display',
            'last_inspection_date', 'created_at', 'updated_at',
        ]


class DeviceCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = [
            'category', 'code', 'name', 'area',
            'responsible_person', 'inspection_cycle_days', 'last_inspection_date',
        ]


class DeviceRecordSerializer(serializers.ModelSerializer):
    record_type_display = serializers.CharField(source='get_record_type_display', read_only=True)
    status_from_display = serializers.CharField(source='get_status_from_display', default='', read_only=True)
    status_to_display = serializers.CharField(source='get_status_to_display', default='', read_only=True)
    fault_level_display = serializers.CharField(source='get_fault_level_display', default='', read_only=True)
    operator_name = serializers.CharField(source='operator.username', default='', read_only=True)
    reviewer_name = serializers.CharField(source='reviewer.username', default='', read_only=True)

    class Meta:
        model = DeviceRecord
        fields = [
            'id', 'device', 'record_type', 'record_type_display',
            'status_from', 'status_from_display',
            'status_to', 'status_to_display',
            'fault_level', 'fault_level_display',
            'description', 'operator', 'operator_name',
            'reviewer', 'reviewer_name',
            'review_comment', 'reviewed_at',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['operator', 'reviewer', 'reviewed_at', 'is_active']


class FaultRegisterSerializer(serializers.Serializer):
    device = serializers.IntegerField()
    fault_level = serializers.ChoiceField(choices=['low', 'medium', 'high'])
    description = serializers.CharField(required=False, default='')


class BorrowSerializer(serializers.Serializer):
    device = serializers.IntegerField()
    description = serializers.CharField(required=False, default='')


class ReturnSerializer(serializers.Serializer):
    device = serializers.IntegerField()
    description = serializers.CharField(required=False, default='')


class CleaningSerializer(serializers.Serializer):
    device = serializers.IntegerField()
    description = serializers.CharField(required=False, default='')


class SuspendSerializer(serializers.Serializer):
    device = serializers.IntegerField()
    description = serializers.CharField(required=False, default='')


class InspectSerializer(serializers.Serializer):
    device = serializers.IntegerField()
    description = serializers.CharField(required=False, default='')


class ReviewSerializer(serializers.Serializer):
    record = serializers.IntegerField()
    review_comment = serializers.CharField()


class RestoreSerializer(serializers.Serializer):
    device = serializers.IntegerField()
    description = serializers.CharField(required=False, default='')


class DeviceDetailSerializer(serializers.Serializer):
    device = DeviceListSerializer()
    latest_record = DeviceRecordSerializer(allow_null=True)
    flow_records = DeviceRecordSerializer(many=True)
