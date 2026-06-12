import django_filters
from django.db.models import Q, F, ExpressionWrapper, IntegerField, DateField
from django.utils import timezone
from devices.models import Device, DeviceRecord, InspectionStatus, INSPECTION_WARNING_DAYS


class InspectionStatusFilter(django_filters.CharFilter):
    def filter(self, qs, value):
        if not value:
            return qs
        today = timezone.now().date()
        warning_days = INSPECTION_WARNING_DAYS

        has_last = Q(last_inspection_date__isnull=False)
        days_expr = ExpressionWrapper(
            F('last_inspection_date') + F('inspection_cycle_days') - today,
            output_field=IntegerField()
        )

        if value == InspectionStatus.OVERDUE:
            overdue_qs = qs.filter(last_inspection_date__isnull=True)
            due_qs = qs.annotate(days=days_expr).filter(has_last, days__lt=0)
            return overdue_qs | due_qs
        elif value == InspectionStatus.DUE_SOON:
            return qs.annotate(days=days_expr).filter(has_last, days__gte=0, days__lte=warning_days)
        elif value == InspectionStatus.NOT_DUE:
            return qs.annotate(days=days_expr).filter(has_last, days__gt=warning_days)
        return qs


class DeviceFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name='category', lookup_expr='exact')
    area = django_filters.NumberFilter(field_name='area__id')
    responsible_person = django_filters.NumberFilter(field_name='responsible_person__id')
    status = django_filters.CharFilter(field_name='status', lookup_expr='exact')
    inspection_status = InspectionStatusFilter()
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Device
        fields = ['category', 'area', 'responsible_person', 'status', 'inspection_status', 'created_after', 'created_before']


class DeviceRecordFilter(django_filters.FilterSet):
    device = django_filters.NumberFilter(field_name='device__id')
    device_code = django_filters.CharFilter(field_name='device__code', lookup_expr='icontains')
    record_type = django_filters.CharFilter(field_name='record_type', lookup_expr='exact')
    fault_level = django_filters.CharFilter(field_name='fault_level', lookup_expr='exact')
    status_from = django_filters.CharFilter(field_name='status_from', lookup_expr='exact')
    status_to = django_filters.CharFilter(field_name='status_to', lookup_expr='exact')
    is_active = django_filters.BooleanFilter(field_name='is_active')
    category = django_filters.CharFilter(field_name='device__category', lookup_expr='exact')
    area = django_filters.NumberFilter(field_name='device__area__id')
    responsible_person = django_filters.NumberFilter(field_name='device__responsible_person__id')
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = DeviceRecord
        fields = [
            'device', 'device_code', 'record_type', 'fault_level',
            'status_from', 'status_to', 'is_active',
            'category', 'area', 'responsible_person',
            'created_after', 'created_before',
        ]
