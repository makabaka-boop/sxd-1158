from django.utils import timezone
from django.db.models import Count, F, DurationField, ExpressionWrapper, Avg, Q, IntegerField
from devices.models import (
    Device, DeviceRecord, DeviceStatus, RecordType, Role,
    InspectionStatus, INSPECTION_WARNING_DAYS,
)


ACTIVE_STATUSES = {
    DeviceStatus.BORROWED,
    DeviceStatus.PENDING_INSPECTION,
    DeviceStatus.PROCESSING,
    DeviceStatus.PENDING_REVIEW,
    DeviceStatus.SUSPENDED,
}

DUTY_RECORD_TYPES = {
    RecordType.FAULT,
    RecordType.BORROW,
    RecordType.CLEANING,
    RecordType.SUSPEND,
}

STATUS_FLOW = {
    DeviceStatus.AVAILABLE: {
        RecordType.FAULT: DeviceStatus.PENDING_INSPECTION,
        RecordType.BORROW: DeviceStatus.BORROWED,
        RecordType.CLEANING: None,
        RecordType.SUSPEND: DeviceStatus.SUSPENDED,
    },
    DeviceStatus.PENDING_INSPECTION: {
        RecordType.INSPECT: DeviceStatus.PROCESSING,
    },
    DeviceStatus.PROCESSING: {
        RecordType.INSPECT: DeviceStatus.PENDING_REVIEW,
    },
    DeviceStatus.PENDING_REVIEW: {
        RecordType.REVIEW: DeviceStatus.RESTORED,
    },
    DeviceStatus.RESTORED: {
        RecordType.RESTORE: DeviceStatus.AVAILABLE,
        RecordType.FAULT: DeviceStatus.PENDING_INSPECTION,
        RecordType.BORROW: DeviceStatus.BORROWED,
        RecordType.CLEANING: None,
        RecordType.SUSPEND: DeviceStatus.SUSPENDED,
    },
    DeviceStatus.BORROWED: {
        RecordType.RETURN: DeviceStatus.AVAILABLE,
        RecordType.FAULT: DeviceStatus.PENDING_INSPECTION,
    },
    DeviceStatus.SUSPENDED: {
        RecordType.FAULT: DeviceStatus.PENDING_INSPECTION,
    },
}


def check_duplicate_active_record(device, record_type):
    if record_type == RecordType.CLEANING:
        return False
    if device.status not in [DeviceStatus.BORROWED, DeviceStatus.PROCESSING,
                             DeviceStatus.PENDING_INSPECTION, DeviceStatus.PENDING_REVIEW]:
        return False
    exists = DeviceRecord.objects.filter(
        device=device,
        record_type=record_type,
        is_active=True,
    ).exists()
    return exists


def validate_status_transition(device, record_type):
    current_status = device.status
    if current_status not in STATUS_FLOW:
        return False, f'当前状态 {device.get_status_display()} 不允许任何操作'

    allowed = STATUS_FLOW[current_status]
    if record_type not in allowed:
        return False, f'当前状态 {device.get_status_display()} 不允许执行 {record_type} 操作'

    return True, None


def create_record(device, record_type, operator, description='', fault_level=None):
    old_status = device.status
    is_valid, error = validate_status_transition(device, record_type)
    if not is_valid and record_type != RecordType.CLEANING:
        return None, error

    if check_duplicate_active_record(device, record_type):
        return None, f'设备 {device.code} 在 {device.get_status_display()} 状态下已存在同类活跃事项，不可重复登记'

    new_status = STATUS_FLOW.get(old_status, {}).get(record_type)

    record = DeviceRecord.objects.create(
        device=device,
        record_type=record_type,
        status_from=old_status,
        status_to=new_status,
        fault_level=fault_level,
        description=description,
        operator=operator,
    )

    if new_status is not None:
        device.status = new_status
        device.save(update_fields=['status', 'updated_at'])

    return record, None


def create_fault_record(device, operator, fault_level, description=''):
    if device.status == DeviceStatus.BORROWED:
        DeviceRecord.objects.filter(
            device=device,
            record_type=RecordType.BORROW,
            is_active=True,
        ).update(is_active=False)
    return create_record(
        device=device,
        record_type=RecordType.FAULT,
        operator=operator,
        description=description,
        fault_level=fault_level,
    )


def create_borrow_record(device, operator, description=''):
    return create_record(
        device=device,
        record_type=RecordType.BORROW,
        operator=operator,
        description=description,
    )


def create_return_record(device, operator, description=''):
    record, error = create_record(
        device=device,
        record_type=RecordType.RETURN,
        operator=operator,
        description=description,
    )
    if record:
        DeviceRecord.objects.filter(
            device=device,
            record_type=RecordType.BORROW,
            is_active=True,
        ).update(is_active=False)
    return record, error


def create_cleaning_record(device, operator, description=''):
    record = DeviceRecord.objects.create(
        device=device,
        record_type=RecordType.CLEANING,
        status_from=device.status,
        status_to=None,
        description=description,
        operator=operator,
    )
    return record, None


def create_suspend_record(device, operator, description=''):
    record, error = create_record(
        device=device,
        record_type=RecordType.SUSPEND,
        operator=operator,
        description=description,
    )
    if record:
        DeviceRecord.objects.filter(
            device=device,
            is_active=True,
        ).exclude(record_type=RecordType.SUSPEND).update(is_active=False)
    return record, error


def create_inspect_record(device, operator, description=''):
    if device.status == DeviceStatus.PENDING_INSPECTION:
        return create_record(
            device=device,
            record_type=RecordType.INSPECT,
            operator=operator,
            description=description or '开始检修处理',
        )
    elif device.status == DeviceStatus.PROCESSING:
        DeviceRecord.objects.filter(
            device=device,
            record_type=RecordType.INSPECT,
            is_active=True,
        ).update(is_active=False)
        return create_record(
            device=device,
            record_type=RecordType.INSPECT,
            operator=operator,
            description=description or '检修完成，提交复核',
        )
    else:
        return None, f'设备当前状态为 {device.get_status_display()}，不允许检修操作'


def create_review_record(record_id, reviewer, review_comment):
    try:
        original = DeviceRecord.objects.get(id=record_id, is_active=True)
    except DeviceRecord.DoesNotExist:
        return None, '记录不存在或已关闭'

    device = original.device

    if device.status != DeviceStatus.PENDING_REVIEW:
        return None, f'设备当前状态为 {device.get_status_display()}，不允许复核，需先提交复核申请'

    new_status = STATUS_FLOW[DeviceStatus.PENDING_REVIEW][RecordType.REVIEW]

    review_record = DeviceRecord.objects.create(
        device=device,
        record_type=RecordType.REVIEW,
        status_from=device.status,
        status_to=new_status,
        description=f'复核原始记录 #{original.id}',
        operator=reviewer,
        reviewer=reviewer,
        review_comment=review_comment,
        reviewed_at=timezone.now(),
    )

    DeviceRecord.objects.filter(
        device=device,
        is_active=True,
    ).update(
        reviewer=reviewer,
        review_comment=review_comment,
        reviewed_at=timezone.now(),
        is_active=False,
    )

    device.status = new_status
    device.save(update_fields=['status', 'updated_at'])

    return review_record, None


def create_restore_record(device, operator, description=''):
    is_valid, error = validate_status_transition(device, RecordType.RESTORE)
    if not is_valid:
        return None, error

    DeviceRecord.objects.filter(device=device, is_active=True).update(is_active=False)

    device.status = DeviceStatus.AVAILABLE
    device.last_inspection_date = timezone.now().date()
    device.save(update_fields=['status', 'last_inspection_date', 'updated_at'])

    record = DeviceRecord.objects.create(
        device=device,
        record_type=RecordType.RESTORE,
        status_from=DeviceStatus.RESTORED,
        status_to=DeviceStatus.AVAILABLE,
        description=description or '设备恢复正常，重新可用',
        operator=operator,
        is_active=False,
    )
    return record, None


def get_pending_review_list():
    return DeviceRecord.objects.filter(
        is_active=True,
        device__status=DeviceStatus.PENDING_REVIEW,
    ).select_related('device', 'operator').order_by('-created_at')


def get_area_issue_distribution():
    return (
        DeviceRecord.objects
        .filter(record_type=RecordType.FAULT)
        .values(area_name=F('device__area__name'), area_id=F('device__area__id'))
        .annotate(fault_count=Count('id'))
        .order_by('-fault_count')
    )


def get_responsible_person_time_ranking():
    records = (
        DeviceRecord.objects
        .filter(
            record_type=RecordType.REVIEW,
            reviewed_at__isnull=False,
        )
        .values(responsible_person=F('device__responsible_person__username'))
        .annotate(
            avg_duration=ExpressionWrapper(
                Avg(F('reviewed_at') - F('created_at')),
                output_field=DurationField(),
            )
        )
        .order_by('avg_duration')
    )
    return records


def _get_days_expr():
    today = timezone.now().date()
    return ExpressionWrapper(
        F('last_inspection_date') + F('inspection_cycle_days') - today,
        output_field=IntegerField()
    )


def get_overdue_devices():
    days_expr = _get_days_expr()
    no_last = Q(last_inspection_date__isnull=True)
    overdue = Q(last_inspection_date__isnull=False) & Q(days__lt=0)
    return (
        Device.objects
        .select_related('area', 'responsible_person')
        .annotate(days=days_expr)
        .filter(no_last | overdue)
        .order_by('last_inspection_date')
    )


def get_due_soon_devices():
    days_expr = _get_days_expr()
    return (
        Device.objects
        .select_related('area', 'responsible_person')
        .annotate(days=days_expr)
        .filter(last_inspection_date__isnull=False, days__gte=0, days__lte=INSPECTION_WARNING_DAYS)
        .order_by('days')
    )


def get_inspection_summary_by_area():
    days_expr = _get_days_expr()
    annotated_qs = Device.objects.annotate(days=days_expr)
    overdue_qs = annotated_qs.filter(
        Q(last_inspection_date__isnull=True) | Q(days__lt=0)
    )
    due_soon_qs = annotated_qs.filter(
        last_inspection_date__isnull=False, days__gte=0, days__lte=INSPECTION_WARNING_DAYS
    )
    overdue_data = list(
        overdue_qs
        .values(aid=F('area__id'), aname=F('area__name'))
        .annotate(count=Count('id'))
    )
    due_soon_data = list(
        due_soon_qs
        .values(aid=F('area__id'), aname=F('area__name'))
        .annotate(count=Count('id'))
    )
    overdue_map = {item['aid']: item['count'] for item in overdue_data}
    due_soon_map = {item['aid']: item['count'] for item in due_soon_data}
    all_areas = list(
        Device.objects
        .values(aid=F('area__id'), aname=F('area__name'))
        .distinct()
    )
    seen = set()
    result = []
    for a in all_areas:
        aid = a['aid']
        if aid in seen:
            continue
        seen.add(aid)
        result.append({
            'area_id': aid,
            'area_name': a['aname'] or '未分配区域',
            'overdue_count': overdue_map.get(aid, 0),
            'due_soon_count': due_soon_map.get(aid, 0),
        })
    result.sort(key=lambda x: -(x['overdue_count'] + x['due_soon_count']))
    return result


def get_inspection_summary_by_responsible_person():
    days_expr = _get_days_expr()
    annotated_qs = Device.objects.annotate(days=days_expr)
    overdue_qs = annotated_qs.filter(
        Q(last_inspection_date__isnull=True) | Q(days__lt=0)
    )
    due_soon_qs = annotated_qs.filter(
        last_inspection_date__isnull=False, days__gte=0, days__lte=INSPECTION_WARNING_DAYS
    )
    overdue_data = list(
        overdue_qs
        .values(pid=F('responsible_person__id'), pname=F('responsible_person__username'))
        .annotate(count=Count('id'))
    )
    due_soon_data = list(
        due_soon_qs
        .values(pid=F('responsible_person__id'), pname=F('responsible_person__username'))
        .annotate(count=Count('id'))
    )
    overdue_map = {item['pid']: item['count'] for item in overdue_data}
    due_soon_map = {item['pid']: item['count'] for item in due_soon_data}
    all_persons = list(
        Device.objects
        .values(pid=F('responsible_person__id'), pname=F('responsible_person__username'))
        .distinct()
    )
    seen = set()
    result = []
    for p in all_persons:
        pid = p['pid']
        if pid in seen:
            continue
        seen.add(pid)
        result.append({
            'responsible_person_id': pid,
            'responsible_person_name': p['pname'] or '未指定责任人',
            'overdue_count': overdue_map.get(pid, 0),
            'due_soon_count': due_soon_map.get(pid, 0),
        })
    result.sort(key=lambda x: -(x['overdue_count'] + x['due_soon_count']))
    return result


def get_inspection_reminder_statistics():
    from devices.serializers import DeviceListSerializer
    overdue_devices = get_overdue_devices()
    due_soon_devices = get_due_soon_devices()
    return {
        'total_overdue': overdue_devices.count(),
        'total_due_soon': due_soon_devices.count(),
        'overdue_devices': DeviceListSerializer(overdue_devices, many=True).data,
        'due_soon_devices': DeviceListSerializer(due_soon_devices, many=True).data,
        'summary_by_area': get_inspection_summary_by_area(),
        'summary_by_responsible_person': get_inspection_summary_by_responsible_person(),
    }
