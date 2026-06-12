from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from devices.views import (
    RegisterView, UserListView,
    AreaListCreateView, AreaDetailView,
    DeviceListCreateView, DeviceDetailView, DeviceDetailFullView,
    FaultRegisterView, BorrowView, ReturnView,
    CleaningView, SuspendView,
    InspectView, ReviewConfirmView, RestoreView,
    DeviceRecordListView,
    PendingReviewListView, AreaIssueDistributionView,
    ResponsiblePersonTimeRankingView,
)

urlpatterns = [
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/register/', RegisterView.as_view(), name='register'),

    path('users/', UserListView.as_view(), name='user-list'),

    path('areas/', AreaListCreateView.as_view(), name='area-list-create'),
    path('areas/<int:pk>/', AreaDetailView.as_view(), name='area-detail'),

    path('devices/', DeviceListCreateView.as_view(), name='device-list-create'),
    path('devices/<int:pk>/', DeviceDetailView.as_view(), name='device-detail'),
    path('devices/<int:pk>/detail/', DeviceDetailFullView.as_view(), name='device-detail-full'),

    path('records/fault/', FaultRegisterView.as_view(), name='fault-register'),
    path('records/borrow/', BorrowView.as_view(), name='borrow'),
    path('records/return/', ReturnView.as_view(), name='return'),
    path('records/cleaning/', CleaningView.as_view(), name='cleaning'),
    path('records/suspend/', SuspendView.as_view(), name='suspend'),
    path('records/inspect/', InspectView.as_view(), name='inspect'),
    path('records/review/', ReviewConfirmView.as_view(), name='review-confirm'),
    path('records/restore/', RestoreView.as_view(), name='restore'),

    path('records/', DeviceRecordListView.as_view(), name='record-list'),

    path('stats/pending-review/', PendingReviewListView.as_view(), name='pending-review'),
    path('stats/area-issues/', AreaIssueDistributionView.as_view(), name='area-issues'),
    path('stats/responsible-time/', ResponsiblePersonTimeRankingView.as_view(), name='responsible-time'),
]
