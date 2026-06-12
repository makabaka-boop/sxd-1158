from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth.models import User
from django.utils import timezone

from devices.models import (
    Device, DeviceRecord, DeviceStatus, Area, UserProfile, Role,
)
from devices.permissions import IsAdmin, IsAdminOrDuty, IsAdminOrReviewer, IsReviewer
from devices.serializers import (
    UserSerializer, AreaSerializer, DeviceListSerializer,
    DeviceCreateUpdateSerializer, DeviceRecordSerializer,
    FaultRegisterSerializer, BorrowSerializer, ReturnSerializer,
    CleaningSerializer, SuspendSerializer, InspectSerializer,
    ReviewSerializer, RestoreSerializer, DeviceDetailSerializer,
)
from devices.services import (
    create_fault_record, create_borrow_record, create_return_record,
    create_cleaning_record, create_suspend_record, create_inspect_record,
    create_review_record, create_restore_record,
    get_pending_review_list, get_area_issue_distribution,
    get_responsible_person_time_ranking,
)
from devices.filters import DeviceFilter, DeviceRecordFilter


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]


class AreaListCreateView(generics.ListCreateAPIView):
    queryset = Area.objects.all()
    serializer_class = AreaSerializer
    permission_classes = [IsAdminOrDuty]


class AreaDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Area.objects.all()
    serializer_class = AreaSerializer
    permission_classes = [IsAdmin]


class DeviceListCreateView(generics.ListCreateAPIView):
    queryset = Device.objects.select_related('area', 'responsible_person').all()
    permission_classes = [IsAuthenticated]
    filterset_class = DeviceFilter

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return DeviceCreateUpdateSerializer
        return DeviceListSerializer

    def perform_create(self, serializer):
        serializer.save()


class DeviceDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Device.objects.select_related('area', 'responsible_person').all()
    permission_classes = [IsAdmin]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return DeviceCreateUpdateSerializer
        return DeviceListSerializer


class DeviceDetailFullView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            device = Device.objects.select_related(
                'area', 'responsible_person'
            ).get(pk=pk)
        except Device.DoesNotExist:
            return Response({'detail': '设备不存在'}, status=status.HTTP_404_NOT_FOUND)

        flow_records = DeviceRecord.objects.filter(
            device=device
        ).select_related('operator', 'reviewer').order_by('-created_at')

        latest_record = flow_records.first()

        serializer = DeviceDetailSerializer({
            'device': device,
            'latest_record': latest_record,
            'flow_records': flow_records,
        })
        return Response(serializer.data)


class FaultRegisterView(APIView):
    permission_classes = [IsAdminOrDuty]

    def post(self, request):
        serializer = FaultRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            device = Device.objects.get(pk=serializer.validated_data['device'])
        except Device.DoesNotExist:
            return Response({'detail': '设备不存在'}, status=status.HTTP_404_NOT_FOUND)

        record, error = create_fault_record(
            device=device,
            operator=request.user,
            fault_level=serializer.validated_data['fault_level'],
            description=serializer.validated_data.get('description', ''),
        )
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            DeviceRecordSerializer(record).data,
            status=status.HTTP_201_CREATED,
        )


class BorrowView(APIView):
    permission_classes = [IsAdminOrDuty]

    def post(self, request):
        serializer = BorrowSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            device = Device.objects.get(pk=serializer.validated_data['device'])
        except Device.DoesNotExist:
            return Response({'detail': '设备不存在'}, status=status.HTTP_404_NOT_FOUND)

        record, error = create_borrow_record(
            device=device,
            operator=request.user,
            description=serializer.validated_data.get('description', ''),
        )
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            DeviceRecordSerializer(record).data,
            status=status.HTTP_201_CREATED,
        )


class ReturnView(APIView):
    permission_classes = [IsAdminOrDuty]

    def post(self, request):
        serializer = ReturnSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            device = Device.objects.get(pk=serializer.validated_data['device'])
        except Device.DoesNotExist:
            return Response({'detail': '设备不存在'}, status=status.HTTP_404_NOT_FOUND)

        record, error = create_return_record(
            device=device,
            operator=request.user,
            description=serializer.validated_data.get('description', ''),
        )
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            DeviceRecordSerializer(record).data,
            status=status.HTTP_201_CREATED,
        )


class CleaningView(APIView):
    permission_classes = [IsAdminOrDuty]

    def post(self, request):
        serializer = CleaningSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            device = Device.objects.get(pk=serializer.validated_data['device'])
        except Device.DoesNotExist:
            return Response({'detail': '设备不存在'}, status=status.HTTP_404_NOT_FOUND)

        record, error = create_cleaning_record(
            device=device,
            operator=request.user,
            description=serializer.validated_data.get('description', ''),
        )

        return Response(
            DeviceRecordSerializer(record).data,
            status=status.HTTP_201_CREATED,
        )


class SuspendView(APIView):
    permission_classes = [IsAdminOrDuty]

    def post(self, request):
        serializer = SuspendSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            device = Device.objects.get(pk=serializer.validated_data['device'])
        except Device.DoesNotExist:
            return Response({'detail': '设备不存在'}, status=status.HTTP_404_NOT_FOUND)

        record, error = create_suspend_record(
            device=device,
            operator=request.user,
            description=serializer.validated_data.get('description', ''),
        )
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            DeviceRecordSerializer(record).data,
            status=status.HTTP_201_CREATED,
        )


class InspectView(APIView):
    permission_classes = [IsAdminOrReviewer]

    def post(self, request):
        serializer = InspectSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            device = Device.objects.get(pk=serializer.validated_data['device'])
        except Device.DoesNotExist:
            return Response({'detail': '设备不存在'}, status=status.HTTP_404_NOT_FOUND)

        record, error = create_inspect_record(
            device=device,
            operator=request.user,
            description=serializer.validated_data.get('description', ''),
        )
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            DeviceRecordSerializer(record).data,
            status=status.HTTP_201_CREATED,
        )


class ReviewConfirmView(APIView):
    permission_classes = [IsReviewer]

    def post(self, request):
        serializer = ReviewSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        record, error = create_review_record(
            record_id=serializer.validated_data['record'],
            reviewer=request.user,
            review_comment=serializer.validated_data['review_comment'],
        )
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            DeviceRecordSerializer(record).data,
            status=status.HTTP_201_CREATED,
        )


class RestoreView(APIView):
    permission_classes = [IsAdminOrReviewer]

    def post(self, request):
        serializer = RestoreSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            device = Device.objects.get(pk=serializer.validated_data['device'])
        except Device.DoesNotExist:
            return Response({'detail': '设备不存在'}, status=status.HTTP_404_NOT_FOUND)

        record, error = create_restore_record(
            device=device,
            operator=request.user,
            description=serializer.validated_data.get('description', ''),
        )
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            DeviceRecordSerializer(record).data,
            status=status.HTTP_201_CREATED,
        )


class DeviceRecordListView(generics.ListAPIView):
    queryset = DeviceRecord.objects.select_related(
        'device', 'operator', 'reviewer'
    ).all()
    serializer_class = DeviceRecordSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = DeviceRecordFilter


class PendingReviewListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        records = get_pending_review_list()
        serializer = DeviceRecordSerializer(records, many=True)
        return Response(serializer.data)


class AreaIssueDistributionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = get_area_issue_distribution()
        result = []
        for item in data:
            result.append({
                'area_id': item['area_id'],
                'area_name': item['area_name'] or '未分配区域',
                'fault_count': item['fault_count'],
            })
        return Response(result)


class ResponsiblePersonTimeRankingView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = get_responsible_person_time_ranking()
        result = []
        for item in data:
            avg = item['avg_duration']
            result.append({
                'responsible_person': item['responsible_person'] or '未指定',
                'avg_duration_seconds': avg.total_seconds() if avg else None,
                'avg_duration_display': str(avg) if avg else None,
            })
        return Response(result)
