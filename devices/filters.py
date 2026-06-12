import django_filters
from devices.models import Device, DeviceRecord


class DeviceFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name='category', lookup_expr='exact')
    area = django_filters.NumberFilter(field_name='area__id')
    responsible_person = django_filters.NumberFilter(field_name='responsible_person__id')
    status = django_filters.CharFilter(field_name='status', lookup_expr='exact')
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Device
        fields = ['category', 'area', 'responsible_person', 'status', 'created_after', 'created_before']


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
