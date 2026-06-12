from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


class Role(models.TextChoices):
    ADMIN = 'admin', '管理员'
    DUTY = 'duty', '值班人员'
    REVIEWER = 'reviewer', '复核人员'


class DeviceCategory(models.TextChoices):
    HEADPHONE = 'headphone', '耳机'
    CARD_READER = 'card_reader', '读卡器'
    RESERVATION_SCREEN = 'reservation_screen', '预约屏'
    SEAT_INDICATOR = 'seat_indicator', '座位提示器'


class DeviceStatus(models.TextChoices):
    AVAILABLE = 'available', '可使用'
    BORROWED = 'borrowed', '已借出'
    PENDING_INSPECTION = 'pending_inspection', '待检修'
    PROCESSING = 'processing', '处理中'
    PENDING_REVIEW = 'pending_review', '待复核'
    RESTORED = 'restored', '恢复可用'
    SUSPENDED = 'suspended', '停用留置'


class InspectionStatus(models.TextChoices):
    NOT_DUE = 'not_due', '未到期'
    DUE_SOON = 'due_soon', '即将到期'
    OVERDUE = 'overdue', '已逾期'


INSPECTION_WARNING_DAYS = 7


class RecordType(models.TextChoices):
    FAULT = 'fault', '故障登记'
    BORROW = 'borrow', '借用'
    RETURN = 'return', '归还'
    CLEANING = 'cleaning', '清洁记录'
    SUSPEND = 'suspend', '临时停用'
    INSPECT = 'inspect', '检修处理'
    REVIEW = 'review', '复核确认'
    RESTORE = 'restore', '恢复可用'


class FaultLevel(models.TextChoices):
    LOW = 'low', '低'
    MEDIUM = 'medium', '中'
    HIGH = 'high', '高'


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.DUTY)

    class Meta:
        verbose_name = '用户角色'
        verbose_name_plural = '用户角色'

    def __str__(self):
        return f'{self.user.username} - {self.get_role_display()}'


class Area(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='区域名称')

    class Meta:
        verbose_name = '区域'
        verbose_name_plural = '区域'

    def __str__(self):
        return self.name


class Device(models.Model):
    category = models.CharField(max_length=30, choices=DeviceCategory.choices, verbose_name='设备类别')
    code = models.CharField(max_length=50, unique=True, verbose_name='设备编号')
    name = models.CharField(max_length=200, verbose_name='设备名称')
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='所在区域')
    responsible_person = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='responsible_devices', verbose_name='责任人'
    )
    inspection_cycle_days = models.PositiveIntegerField(default=30, verbose_name='检修周期(天)')
    status = models.CharField(
        max_length=30, choices=DeviceStatus.choices,
        default=DeviceStatus.AVAILABLE, verbose_name='设备状态'
    )
    last_inspection_date = models.DateField(null=True, blank=True, verbose_name='上次检修日期')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '设备'
        verbose_name_plural = '设备'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_category_display()} - {self.code}'

    @property
    def next_inspection_date(self):
        if not self.last_inspection_date:
            return None
        return self.last_inspection_date + timedelta(days=self.inspection_cycle_days)

    @property
    def days_until_inspection(self):
        next_date = self.next_inspection_date
        if next_date is None:
            return None
        today = timezone.now().date()
        return (next_date - today).days

    @property
    def inspection_status(self):
        days = self.days_until_inspection
        if days is None:
            return InspectionStatus.OVERDUE
        if days < 0:
            return InspectionStatus.OVERDUE
        if days <= INSPECTION_WARNING_DAYS:
            return InspectionStatus.DUE_SOON
        return InspectionStatus.NOT_DUE

    @property
    def inspection_status_display(self):
        return InspectionStatus(self.inspection_status).label


class DeviceRecord(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='records', verbose_name='设备')
    record_type = models.CharField(max_length=20, choices=RecordType.choices, verbose_name='记录类型')
    status_from = models.CharField(
        max_length=30, choices=DeviceStatus.choices,
        null=True, blank=True, verbose_name='流转前状态'
    )
    status_to = models.CharField(
        max_length=30, choices=DeviceStatus.choices,
        null=True, blank=True, verbose_name='流转后状态'
    )
    fault_level = models.CharField(
        max_length=10, choices=FaultLevel.choices,
        null=True, blank=True, verbose_name='故障等级'
    )
    description = models.TextField(blank=True, default='', verbose_name='说明')
    operator = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='operated_records', verbose_name='操作人'
    )
    reviewer = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_records', verbose_name='复核人'
    )
    review_comment = models.TextField(blank=True, default='', verbose_name='复核意见')
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='复核时间')
    is_active = models.BooleanField(default=True, verbose_name='是否活跃')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '设备记录'
        verbose_name_plural = '设备记录'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.device.code} - {self.get_record_type_display()} - {self.created_at}'
