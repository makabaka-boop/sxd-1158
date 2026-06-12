from django.contrib import admin
from devices.models import UserProfile, Area, Device, DeviceRecord


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role']
    list_filter = ['role']


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'category', 'area', 'responsible_person', 'status', 'inspection_cycle_days']
    list_filter = ['category', 'status', 'area']
    search_fields = ['code', 'name']


@admin.register(DeviceRecord)
class DeviceRecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'device', 'record_type', 'status_from', 'status_to', 'operator', 'is_active', 'created_at']
    list_filter = ['record_type', 'is_active', 'fault_level']
