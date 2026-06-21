from django.conf import settings
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.settlements.api.serializers import (
    GroupBalancesResponseSerializer,
    GroupDebtsResponseSerializer,
    ManualSettlementCreateSerializer,
    ManualSettlementItemSerializer,
    ManualSettlementListResponseSerializer,
    GroupRunReminderRequestSerializer,
    GroupRunReminderResponseSerializer,
    ManualReminderSendResponseSerializer,
    ManualReminderSendSerializer,
    MessageSerializer,
    ReminderDetailSerializer,
    ReminderHistoryItemSerializer,
    ReminderHistoryListSerializer,
    ReminderSettingsPatchSerializer,
    ReminderSettingsSerializer,
    MyBalanceResponseSerializer,
    MessageWithManualSettlementSerializer,
    SettlementPlanDetailSerializer,
    SettlementPlanGenerateSerializer,
    SettlementPlanRejectItemSerializer,
    SettlementPlanReportPaidSerializer,
    SettlementRejectSerializer,
)
from datetime import datetime

from apps.settlements.application.use_cases import (
    CancelSettlementUseCase,
    ConfirmSettlementUseCase,
    CreateManualSettlementUseCase,
    GetGroupBalancesUseCase,
    GetGroupDebtsUseCase,
    GetMyBalanceUseCase,
    ListGroupSettlementsUseCase,
    RejectSettlementUseCase,
)
from apps.settlements.application.reminder_use_cases import (
    GetReminderDetailUseCase,
    GetReminderSettingsUseCase,
    ListReminderHistoryUseCase,
    RunGroupReminderUseCase,
    SendManualItemReminderUseCase,
    UpdateReminderSettingsUseCase,
)
from apps.settlements.application.settlement_plan_use_cases import (
    ActivateSettlementPlanUseCase,
    CancelSettlementPlanUseCase,
    ConfirmPlanItemUseCase,
    GenerateSettlementPlanUseCase,
    GetLatestSettlementPlanUseCase,
    RejectPlanItemUseCase,
    ReportPlanItemPaidUseCase,
)
from apps.settlements.domain.rules import SettlementServiceError
from apps.settlements.domain.plan_rules import SettlementPlanExpiredError
from apps.settlements.application.settlement_plan_service import SettlementPlanService
from apps.settlements.infrastructure.jwt_authentication import JWTAuthentication


def _error_response(exc):
    return Response(
        {"error": {"code": exc.code, "message": exc.message}}, status=exc.status_code
    )


def _parse_optional_datetime(value):
    if value in (None, ""):
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception as exc:
        raise ValueError("Invalid ISO-8601 datetime value.") from exc


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(
            {
                "service": settings.SERVICE_NAME,
                "status": "ok",
                "version": settings.SERVICE_VERSION,
            }
        )


class GroupBalancesView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Settlements"], responses={200: GroupBalancesResponseSerializer}
    )
    def get(self, request, group_id, *args, **kwargs):
        try:
            payload = GetGroupBalancesUseCase().execute(request.user, group_id)
        except SettlementServiceError as exc:
            return _error_response(exc)
        return Response(payload)


class MyBalanceView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Settlements"], responses={200: MyBalanceResponseSerializer})
    def get(self, request, group_id, *args, **kwargs):
        try:
            payload = GetMyBalanceUseCase().execute(request.user, group_id)
        except SettlementServiceError as exc:
            return _error_response(exc)
        if payload is None:
            return _error_response(SettlementServiceError("Balance not available."))
        return Response(payload)


class GroupDebtsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Settlements"], responses={200: GroupDebtsResponseSerializer})
    def get(self, request, group_id, *args, **kwargs):
        try:
            payload = GetGroupDebtsUseCase().execute(request.user, group_id)
        except SettlementServiceError as exc:
            return _error_response(exc)
        return Response(payload)


class GroupSettlementsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Settlements"],
        parameters=[
            OpenApiParameter(
                name="status", type=str, required=False, location=OpenApiParameter.QUERY
            ),
            OpenApiParameter(
                name="payer_user_id",
                type=str,
                required=False,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="receiver_user_id",
                type=str,
                required=False,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={200: ManualSettlementListResponseSerializer},
    )
    def get(self, request, group_id, *args, **kwargs):
        try:
            settlements = ListGroupSettlementsUseCase().execute(
                request.user,
                group_id,
                filters={
                    "status": request.query_params.get("status"),
                    "payer_user_id": request.query_params.get("payer_user_id"),
                    "receiver_user_id": request.query_params.get("receiver_user_id"),
                },
            )
        except SettlementServiceError as exc:
            return _error_response(exc)
        return Response(
            {
                "group_id": str(group_id),
                "settlements": [
                    {
                        "id": str(item.id),
                        "group_id": str(item.group_id),
                        "payer_user_id": str(item.payer_user_id),
                        "receiver_user_id": str(item.receiver_user_id),
                        "amount_minor": item.amount_minor,
                        "currency": item.currency,
                        "status": item.status,
                        "description": item.description,
                        "created_at": item.created_at.isoformat(),
                    }
                    for item in settlements
                ],
            }
        )

    @extend_schema(
        tags=["Settlements"],
        request=ManualSettlementCreateSerializer,
        responses={201: ManualSettlementItemSerializer},
    )
    def post(self, request, group_id, *args, **kwargs):
        serializer = ManualSettlementCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            settlement = CreateManualSettlementUseCase().execute(
                request.user, group_id, serializer.validated_data
            )
        except SettlementServiceError as exc:
            return _error_response(exc)
        return Response(
            {
                "id": str(settlement.id),
                "group_id": str(settlement.group_id),
                "payer_user_id": str(settlement.payer_user_id),
                "receiver_user_id": str(settlement.receiver_user_id),
                "amount_minor": settlement.amount_minor,
                "currency": settlement.currency,
                "status": settlement.status,
                "description": settlement.description,
                "created_at": settlement.created_at.isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )


class ConfirmSettlementView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Settlements"], responses={200: MessageSerializer})
    def post(self, request, settlement_id, *args, **kwargs):
        try:
            ConfirmSettlementUseCase().execute(request.user, settlement_id)
        except SettlementServiceError as exc:
            return _error_response(exc)
        return Response({"message": "Settlement confirmed successfully."})


class RejectSettlementView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Settlements"],
        request=SettlementRejectSerializer,
        responses={200: MessageSerializer},
    )
    def post(self, request, settlement_id, *args, **kwargs):
        serializer = SettlementRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            RejectSettlementUseCase().execute(
                request.user,
                settlement_id,
                reason=serializer.validated_data.get("reason"),
            )
        except SettlementServiceError as exc:
            return _error_response(exc)
        return Response({"message": "Settlement rejected successfully."})


class CancelSettlementView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Settlements"], responses={200: MessageSerializer})
    def post(self, request, settlement_id, *args, **kwargs):
        try:
            CancelSettlementUseCase().execute(request.user, settlement_id)
        except SettlementServiceError as exc:
            return _error_response(exc)
        return Response({"message": "Settlement cancelled successfully."})


class GenerateSettlementPlanView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Settlements"],
        request=SettlementPlanGenerateSerializer,
        responses={201: SettlementPlanDetailSerializer},
    )
    def post(self, request, group_id, *args, **kwargs):
        try:
            plan, items = GenerateSettlementPlanUseCase().execute(
                request.user, group_id
            )
        except SettlementServiceError as exc:
            return _error_response(exc)
        payload = SettlementPlanService()._plan_payload(plan, items)
        return Response(payload, status=status.HTTP_201_CREATED)


class LatestSettlementPlanView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Settlements"], responses={200: SettlementPlanDetailSerializer}
    )
    def get(self, request, group_id, *args, **kwargs):
        try:
            plan, items = GetLatestSettlementPlanUseCase().execute(
                request.user, group_id
            )
        except SettlementServiceError as exc:
            return _error_response(exc)
        return Response(SettlementPlanService()._plan_payload(plan, items))


class ActivateSettlementPlanView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Settlements"], responses={200: MessageSerializer})
    def post(self, request, plan_id, *args, **kwargs):
        try:
            plan = ActivateSettlementPlanUseCase().execute(request.user, plan_id)
            if getattr(plan, "_expired", False):
                return _error_response(SettlementPlanExpiredError())
        except SettlementServiceError as exc:
            return _error_response(exc)
        return Response({"message": "Settlement plan activated successfully."})


class CancelSettlementPlanView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Settlements"], responses={200: MessageSerializer})
    def post(self, request, plan_id, *args, **kwargs):
        try:
            CancelSettlementPlanUseCase().execute(request.user, plan_id)
        except SettlementServiceError as exc:
            return _error_response(exc)
        return Response({"message": "Settlement plan cancelled successfully."})


class ReportPlanItemPaidView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Settlements"],
        request=SettlementPlanReportPaidSerializer,
        responses={200: MessageWithManualSettlementSerializer},
    )
    def post(self, request, item_id, *args, **kwargs):
        serializer = SettlementPlanReportPaidSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            _, settlement = ReportPlanItemPaidUseCase().execute(
                request.user, item_id, serializer.validated_data
            )
        except SettlementServiceError as exc:
            return _error_response(exc)
        return Response(
            {
                "message": "Payment report submitted successfully.",
                "manual_settlement_id": str(settlement.id),
            }
        )


class ConfirmPlanItemView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Settlements"], responses={200: MessageSerializer})
    def post(self, request, item_id, *args, **kwargs):
        try:
            ConfirmPlanItemUseCase().execute(request.user, item_id)
        except SettlementServiceError as exc:
            return _error_response(exc)
        return Response({"message": "Plan item confirmed successfully."})


class RejectPlanItemView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Settlements"],
        request=SettlementPlanRejectItemSerializer,
        responses={200: MessageSerializer},
    )
    def post(self, request, item_id, *args, **kwargs):
        serializer = SettlementPlanRejectItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            RejectPlanItemUseCase().execute(
                request.user, item_id, serializer.validated_data
            )
        except SettlementServiceError as exc:
            return _error_response(exc)
        return Response({"message": "Plan item rejected successfully."})



class GroupReminderSettingsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Settlements"], responses={200: ReminderSettingsSerializer})
    def get(self, request, group_id, *args, **kwargs):
        try:
            payload = GetReminderSettingsUseCase().execute(request.user, group_id)
        except SettlementServiceError as exc:
            return _error_response(exc)
        return Response(payload)

    @extend_schema(
        tags=["Settlements"],
        request=ReminderSettingsPatchSerializer,
        responses={200: ReminderSettingsSerializer},
    )
    def patch(self, request, group_id, *args, **kwargs):
        serializer = ReminderSettingsPatchSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            payload = UpdateReminderSettingsUseCase().execute(
                request.user, group_id, serializer.validated_data
            )
        except SettlementServiceError as exc:
            return _error_response(exc)
        return Response(payload)


class GroupReminderHistoryView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Settlements"],
        parameters=[
            OpenApiParameter(name="status", type=str, required=False, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="recipient_user_id", type=str, required=False, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="settlement_plan_item_id", type=str, required=False, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="source", type=str, required=False, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="from", type=str, required=False, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="to", type=str, required=False, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="cursor", type=str, required=False, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="page_size", type=int, required=False, location=OpenApiParameter.QUERY),
        ],
        responses={200: ReminderHistoryListSerializer},
    )
    def get(self, request, group_id, *args, **kwargs):
        try:
            from_value = _parse_optional_datetime(request.query_params.get("from"))
            to_value = _parse_optional_datetime(request.query_params.get("to"))
            if from_value and to_value and from_value > to_value:
                raise SettlementServiceError("The `from` datetime must be before `to`.")
            items, next_cursor = ListReminderHistoryUseCase().execute(
                request.user,
                group_id,
                filters={
                    "status": request.query_params.get("status"),
                    "recipient_user_id": request.query_params.get("recipient_user_id"),
                    "settlement_plan_item_id": request.query_params.get("settlement_plan_item_id"),
                    "source": request.query_params.get("source"),
                    "from": from_value,
                    "to": to_value,
                    "cursor": request.query_params.get("cursor"),
                    "page_size": request.query_params.get("page_size", 20),
                },
            )
        except ValueError:
            return _error_response(SettlementServiceError("Invalid reminder history filters."))
        except SettlementServiceError as exc:
            return _error_response(exc)
        serializer = ReminderHistoryItemSerializer(
            [GetReminderDetailUseCase().reminder_service.serialize_history_item(item) for item in items],
            many=True,
        )
        return Response({"results": serializer.data, "next_cursor": next_cursor})


class ReminderDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Settlements"], responses={200: ReminderDetailSerializer})
    def get(self, request, reminder_id, *args, **kwargs):
        try:
            reminder = GetReminderDetailUseCase().execute(request.user, reminder_id)
        except SettlementServiceError as exc:
            return _error_response(exc)
        payload = GetReminderDetailUseCase().reminder_service.serialize_detail(reminder)
        return Response(payload)


class RunGroupReminderView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Settlements"],
        request=GroupRunReminderRequestSerializer,
        responses={200: GroupRunReminderResponseSerializer},
    )
    def post(self, request, group_id, *args, **kwargs):
        serializer = GroupRunReminderRequestSerializer(data=request.data or {}, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            payload = RunGroupReminderUseCase().execute(
                request.user,
                group_id,
                dry_run=serializer.validated_data.get("dry_run", False),
            )
        except SettlementServiceError as exc:
            return _error_response(exc)
        return Response(payload)


class ManualItemReminderView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Settlements"],
        request=ManualReminderSendSerializer,
        responses={202: ManualReminderSendResponseSerializer},
    )
    def post(self, request, item_id, *args, **kwargs):
        serializer = ManualReminderSendSerializer(data=request.data or {}, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            reminder = SendManualItemReminderUseCase().execute(
                request.user, item_id, serializer.validated_data
            )
        except SettlementServiceError as exc:
            return _error_response(exc)
        return Response(
            {
                "reminder_id": str(reminder.id),
                "status": reminder.status,
                "channels": list(reminder.channels or []),
            },
            status=status.HTTP_202_ACCEPTED,
        )
