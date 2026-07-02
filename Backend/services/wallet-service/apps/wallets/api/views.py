
from __future__ import annotations

from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpResponseRedirect
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.wallets.api.serializers import (
    CallbackAcceptedSerializer,
    MessageSerializer,
    PaymentGatewayCallbackSerializer,
    PaymentIntentCreateSerializer,
    PaymentIntentSerializer,
    PaymentIntentVerifyResponseSerializer,
    PaymentIntentVerifySerializer,
    WalletSerializer,
    WalletSettlementPayRequestSerializer,
    WalletSettlementPayResponseSerializer,
    WalletSummaryResponseSerializer,
    WalletTransactionItemSerializer,
    WalletTransactionListQuerySerializer,
    WalletTransactionListResponseSerializer,
    WithdrawalCreateSerializer,
    WithdrawalItemSerializer,
    WithdrawalListResponseSerializer,
)
from apps.wallets.application.use_cases import (
    CancelWithdrawalUseCase,
    CreatePaymentIntentUseCase,
    CreateWithdrawalUseCase,
    GetMyWalletUseCase,
    GetPaymentIntentUseCase,
    GetWalletSummaryUseCase,
    GetWalletTransactionUseCase,
    GetWithdrawalUseCase,
    HandleGatewayCallbackUseCase,
    ListWalletTransactionsUseCase,
    ListWithdrawalsUseCase,
    PaySettlementItemWithWalletUseCase,
    VerifyPaymentIntentUseCase,
)
from apps.wallets.domain.rules import WalletServiceError
from apps.wallets.infrastructure.jwt_authentication import JWTAuthentication


def _error_response(exc: WalletServiceError):
    return Response({"error": {"code": exc.code, "message": exc.message}}, status=exc.status_code)


def _is_browser_payment_callback(request) -> bool:
    """Real payment gateways return the customer through a top-level browser navigation.

    Keep API clients and tests on the JSON contract, but send browser callbacks back
    to the React app so users do not get stuck on DRF's browsable API page.
    """
    accept = request.META.get("HTTP_ACCEPT", "")
    sec_fetch_mode = request.META.get("HTTP_SEC_FETCH_MODE", "")
    sec_fetch_dest = request.META.get("HTTP_SEC_FETCH_DEST", "")

    return (
        sec_fetch_mode == "navigate"
        or sec_fetch_dest == "document"
        or ("text/html" in accept and "application/json" not in accept)
    )


def _frontend_payment_result_url(provider: str, payload: dict, *, callback_state: str = "received") -> str:
    explicit_url = str(getattr(settings, "FRONTEND_PAYMENT_RESULT_URL", "")).strip()

    if explicit_url:
        base_url = explicit_url
    else:
        frontend_base_url = str(getattr(settings, "FRONTEND_BASE_URL", "http://localhost:5173")).rstrip("/")
        base_url = f"{frontend_base_url}/payment-result"

    query = {
        "provider": provider,
        "callback_state": callback_state,
    }

    passthrough_keys = [
        "payment_intent_id",
        "intent_id",
        "provider_reference",
        "Authority",
        "authority",
        "Status",
        "status",
        "amount_minor",
        "currency",
        "result",
    ]

    for key in passthrough_keys:
        value = payload.get(key)
        if value not in (None, ""):
            query[key] = str(value)

    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{urlencode(query)}"


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


class WalletMeView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Wallet"], responses={200: WalletSerializer})
    def get(self, request, *args, **kwargs):
        try:
            payload = GetMyWalletUseCase().execute(request.user)
        except WalletServiceError as exc:
            return _error_response(exc)
        return Response(payload)


class WalletTransactionListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Wallet"],
        parameters=[
            OpenApiParameter("type", str, OpenApiParameter.QUERY),
            OpenApiParameter("status", str, OpenApiParameter.QUERY),
            OpenApiParameter("from", str, OpenApiParameter.QUERY),
            OpenApiParameter("to", str, OpenApiParameter.QUERY),
            OpenApiParameter("cursor", str, OpenApiParameter.QUERY),
            OpenApiParameter("page_size", int, OpenApiParameter.QUERY),
        ],
        responses={200: WalletTransactionListResponseSerializer},
    )
    def get(self, request, *args, **kwargs):
        query_data = {}
        if request.query_params.get("type") is not None:
            query_data["type"] = request.query_params.get("type")
        if request.query_params.get("status") is not None:
            query_data["status"] = request.query_params.get("status")
        if request.query_params.get("from") is not None:
            query_data["from_at"] = request.query_params.get("from")
        if request.query_params.get("to") is not None:
            query_data["to"] = request.query_params.get("to")
        if request.query_params.get("cursor") is not None:
            query_data["cursor"] = request.query_params.get("cursor")
        if request.query_params.get("page_size") is not None:
            query_data["page_size"] = request.query_params.get("page_size")
        serializer = WalletTransactionListQuerySerializer(data=query_data)
        if not serializer.is_valid():
            return Response({"error": {"code": "INVALID_REQUEST", "message": "Invalid request data.", "details": serializer.errors}}, status=400)
        try:
            rows, next_cursor = ListWalletTransactionsUseCase().execute(request.user, serializer.validated_data)
        except WalletServiceError as exc:
            return _error_response(exc)
        return Response({"results": rows, "next_cursor": next_cursor})


class WalletTransactionDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Wallet"], responses={200: WalletTransactionItemSerializer})
    def get(self, request, transaction_id, *args, **kwargs):
        try:
            payload = GetWalletTransactionUseCase().execute(request.user, transaction_id)
        except WalletServiceError as exc:
            return _error_response(exc)
        return Response(payload)


class WalletSettlementPayView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Wallet"],
        request=WalletSettlementPayRequestSerializer,
        responses={200: WalletSettlementPayResponseSerializer},
    )
    def post(self, request, item_id, *args, **kwargs):
        serializer = WalletSettlementPayRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": {"code": "INVALID_REQUEST", "message": "Invalid request data.", "details": serializer.errors}}, status=400)
        try:
            payload = PaySettlementItemWithWalletUseCase().execute(
                request.user,
                item_id,
                serializer.validated_data["idempotency_key"],
            )
        except WalletServiceError as exc:
            return _error_response(exc)
        return Response(payload)


class WalletSummaryView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Wallet"], responses={200: WalletSummaryResponseSerializer})
    def get(self, request, *args, **kwargs):
        try:
            payload = GetWalletSummaryUseCase().execute(request.user)
        except WalletServiceError as exc:
            return _error_response(exc)
        return Response(payload)


class WalletWithdrawalListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Wallet"], responses={200: WithdrawalListResponseSerializer})
    def get(self, request, *args, **kwargs):
        try:
            rows = ListWithdrawalsUseCase().execute(request.user)
        except WalletServiceError as exc:
            return _error_response(exc)
        return Response({"results": rows})

    @extend_schema(tags=["Wallet"], request=WithdrawalCreateSerializer, responses={200: WithdrawalItemSerializer})
    def post(self, request, *args, **kwargs):
        serializer = WithdrawalCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": {"code": "INVALID_REQUEST", "message": "Invalid request data.", "details": serializer.errors}}, status=400)
        try:
            payload = CreateWithdrawalUseCase().execute(request.user, serializer.validated_data)
        except WalletServiceError as exc:
            return _error_response(exc)
        return Response(payload)


class WalletWithdrawalDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Wallet"], responses={200: WithdrawalItemSerializer})
    def get(self, request, withdrawal_id, *args, **kwargs):
        try:
            payload = GetWithdrawalUseCase().execute(request.user, withdrawal_id)
        except WalletServiceError as exc:
            return _error_response(exc)
        return Response(payload)


class WalletWithdrawalCancelView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Wallet"], responses={200: WithdrawalItemSerializer})
    def post(self, request, withdrawal_id, *args, **kwargs):
        try:
            payload = CancelWithdrawalUseCase().execute(request.user, withdrawal_id)
        except WalletServiceError as exc:
            return _error_response(exc)
        return Response(payload)


class PaymentIntentListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Payments"],
        request=PaymentIntentCreateSerializer,
        responses={
            201: OpenApiResponse(
                response=PaymentIntentSerializer,
                examples=[
                    OpenApiExample(
                        "Zarinpal create intent",
                        value={
                            "payment_intent_id": "00000000-0000-0000-0000-000000000000",
                            "purpose": "WALLET_TOP_UP",
                            "amount_minor": 1000000,
                            "currency": "IRR",
                            "provider": "ZARINPAL",
                            "status": "REDIRECT_REQUIRED",
                            "payment_url": "https://sandbox.zarinpal.com/pg/StartPay/S000000000000000000000000000000000000",
                            "provider_reference": "S000000000000000000000000000000000000",
                            "expires_at": "2026-06-30T12:00:00Z",
                            "created_at": "2026-06-30T11:30:00Z",
                            "updated_at": "2026-06-30T11:30:00Z",
                            "verified_at": None,
                            "top_up_id": "00000000-0000-0000-0000-000000000001",
                            "wallet_transaction_id": None,
                            "failure_reason": None,
                            "provider_status": "100",
                        },
                        response_only=True,
                    )
                ],
            )
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = PaymentIntentCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": {"code": "INVALID_REQUEST", "message": "Invalid request data.", "details": serializer.errors}}, status=400)
        try:
            payload = CreatePaymentIntentUseCase().execute(request.user, serializer.validated_data)
        except WalletServiceError as exc:
            return _error_response(exc)
        status_code = 200 if payload.get("status") != "REDIRECT_REQUIRED" else 201
        return Response(payload, status=status_code)


class PaymentIntentDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Payments"], responses={200: PaymentIntentSerializer})
    def get(self, request, payment_intent_id, *args, **kwargs):
        try:
            payload = GetPaymentIntentUseCase().execute(request.user, payment_intent_id)
        except WalletServiceError as exc:
            return _error_response(exc)
        return Response(payload)


class PaymentGatewayCallbackView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["Payments"],
        parameters=[
            OpenApiParameter("payment_intent_id", str, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("provider_reference", str, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("Authority", str, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("authority", str, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("Status", str, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("status", str, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("amount_minor", int, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("currency", str, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("result", str, OpenApiParameter.QUERY, required=False),
        ],
        responses={
            200: OpenApiResponse(
                response=CallbackAcceptedSerializer,
                examples=[
                    OpenApiExample(
                        "Zarinpal callback",
                        value={"message": "Callback received."},
                        response_only=True,
                    )
                ],
            ),
            409: OpenApiResponse(response=MessageSerializer),
        },
    )
    def get(self, request, provider, *args, **kwargs):
        serializer = PaymentGatewayCallbackSerializer(data=request.query_params)
        should_redirect = _is_browser_payment_callback(request)

        if not serializer.is_valid():
            if should_redirect:
                redirect_payload = dict(request.query_params.items())
                redirect_payload["error"] = "invalid_callback"
                return HttpResponseRedirect(
                    _frontend_payment_result_url(provider, redirect_payload, callback_state="invalid")
                )
            return Response({"error": {"code": "INVALID_REQUEST", "message": "Invalid request data.", "details": serializer.errors}}, status=400)
        try:
            payload = HandleGatewayCallbackUseCase().execute(provider, serializer.validated_data, method="GET")
        except WalletServiceError as exc:
            if should_redirect:
                redirect_payload = dict(serializer.validated_data)
                redirect_payload["error"] = exc.code
                return HttpResponseRedirect(
                    _frontend_payment_result_url(provider, redirect_payload, callback_state="error")
                )
            return _error_response(exc)

        if should_redirect:
            return HttpResponseRedirect(
                _frontend_payment_result_url(provider, dict(serializer.validated_data), callback_state="received")
            )

        return Response(payload)

    @extend_schema(
        tags=["Payments"],
        request=PaymentGatewayCallbackSerializer,
        responses={200: CallbackAcceptedSerializer},
    )
    def post(self, request, provider, *args, **kwargs):
        serializer = PaymentGatewayCallbackSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": {"code": "INVALID_REQUEST", "message": "Invalid request data.", "details": serializer.errors}}, status=400)
        try:
            payload = HandleGatewayCallbackUseCase().execute(provider, serializer.validated_data, method="POST")
        except WalletServiceError as exc:
            return _error_response(exc)
        return Response(payload)


class PaymentGatewayVerifyView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Payments"],
        request=PaymentIntentVerifySerializer,
        responses={
            200: OpenApiResponse(
                response=PaymentIntentVerifyResponseSerializer,
                examples=[
                    OpenApiExample(
                        "Zarinpal verify succeeded",
                        value={
                            "payment_intent_id": "00000000-0000-0000-0000-000000000000",
                            "top_up_id": "00000000-0000-0000-0000-000000000001",
                            "wallet_transaction_id": "00000000-0000-0000-0000-000000000002",
                            "status": "SUCCEEDED",
                            "amount_minor": 1000000,
                            "currency": "IRR",
                            "provider": "ZARINPAL",
                            "provider_reference": "S000000000000000000000000000000000000",
                            "verified_at": "2026-06-30T12:00:00Z",
                            "wallet_balance_minor": 1000000,
                            "failure_reason": None,
                        },
                        response_only=True,
                    ),
                    OpenApiExample(
                        "Zarinpal verify retryable",
                        value={
                            "payment_intent_id": "00000000-0000-0000-0000-000000000000",
                            "top_up_id": "00000000-0000-0000-0000-000000000001",
                            "wallet_transaction_id": None,
                            "status": "RETRYABLE",
                            "amount_minor": 1000000,
                            "currency": "IRR",
                            "provider": "ZARINPAL",
                            "provider_reference": "S000000000000000000000000000000000000",
                            "verified_at": None,
                            "wallet_balance_minor": 0,
                            "failure_reason": "Provider verification timed out.",
                        },
                        response_only=True,
                    ),
                ],
            ),
            401: OpenApiResponse(response=MessageSerializer),
            404: OpenApiResponse(response=MessageSerializer),
            409: OpenApiResponse(response=MessageSerializer),
        },
    )
    def post(self, request, provider, *args, **kwargs):
        serializer = PaymentIntentVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": {"code": "INVALID_REQUEST", "message": "Invalid request data.", "details": serializer.errors}}, status=400)
        try:
            payload = VerifyPaymentIntentUseCase().execute(request.user, provider, serializer.validated_data)
        except WalletServiceError as exc:
            return _error_response(exc)
        return Response(payload)
