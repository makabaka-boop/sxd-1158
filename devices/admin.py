from django.contrib import admin
from django.db.models import Q, F, ExpressionWrapper, IntegerField
from django.utils.html import format_html
from django.utils import timezone
from devices.models import (
    UserProfile, Area, Device, DeviceRecord,
    InspectionStatus, INSPECTION_WARNING_DAYS,
)


class InspectionStatusListFilter(admin.SimpleListFilter):
    title = '巡检状态'
    parameter_name = 'inspection_status'

    def lookups(self, request, model_admin):
        return InspectionStatus.choices

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset
        today = timezone.now().date()
        warning_days = INSPECTION_WARNING_DAYS
        days_expr = ExpressionWrapper(
            F('last_inspection_date') + F('inspection_cycle_days') - today,
            output_field=IntegerField()
        )
        has_last = Q(last_inspection_date__isnull=False)
        if value == InspectionStatus.OVERDUE:
            overdue_qs = queryset.filter(last_inspection_date__isnull=True)
            due_qs = queryset.annotate(days=days_expr).filter(has_last, days__lt=0)
            return overdue_qs | due_qs
        elif value == InspectionStatus.DUE_SOON:
            return queryset.annotate(days=days_expr).filter(has_last, days__gte=0, days__lte=warning_days)
        elif value == InspectionStatus.NOT_DUE:
            return queryset.annotate(days=days_expr).filter(has_last, days__gt=warning_days)
        return queryset


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role']
    list_filter = ['role']


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = [
        'code', 'name', 'category', 'area', 'responsible_person',
        'status', 'inspection_cycle_days', 'last_inspection_date',
        'next_inspection_date_display', 'days_until_display',
        'inspection_status_colored',
    ]
    list_filter = [
        'category', 'status', 'area', 'responsible_person',
        InspectionStatusListFilter,
    ]
    search_fields = ['code', 'name']
    fieldsets = (
        ('基本信息', {
            'fields': ('category', 'code', 'name', 'area', 'responsible_person')
        }),
        ('巡检配置', {
            'fields': ('inspection_cycle_days', 'last_inspection_date', 'status')
        }),
    )

    def next_inspection_date_display(self, obj):
        return obj.next_inspection_date or '-'
    next_inspection_date_display.short_description = '下次应检日期'

    def days_until_display(self, obj):
        days = obj.days_until_inspection
        if days is None:
            return '-'
        if days < 0:
            return f'逾期{-days}天'
        if days == 0:
            return '今日到期'
        return f'{days}天'
    days_until_display.short_description = '剩余天数'

    def inspection_status_colored(self, obj):
        status = obj.inspection_status
        display = obj.inspection_status_display
        if status == InspectionStatus.OVERDUE:
            color = 'red'
        elif status == InspectionStatus.DUE_SOON:
            color = 'orange'
        else:
            color = 'green'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, display
        )
    inspection_status_colored.short_description = '巡检状态'


@admin.register(DeviceRecord)
class DeviceRecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'device', 'record_type', 'status_from', 'status_to', 'operator', 'is_active', 'created_at']
    list_filter = ['record_type', 'is_active', 'fault_level']
