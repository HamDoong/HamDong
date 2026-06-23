from apps.settlements.application.settlement_plan_service import SettlementPlanService


class GenerateSettlementPlanUseCase:
    def __init__(self, settlement_plan_service=None):
        self.settlement_plan_service = (
            settlement_plan_service or SettlementPlanService()
        )

    def execute(self, user, group_id):
        return self.settlement_plan_service.generate_plan(group_id, user.sub)


class GetLatestSettlementPlanUseCase:
    def __init__(self, settlement_plan_service=None):
        self.settlement_plan_service = (
            settlement_plan_service or SettlementPlanService()
        )

    def execute(self, user, group_id):
        return self.settlement_plan_service.get_latest_plan(group_id, user.sub)


class ActivateSettlementPlanUseCase:
    def __init__(self, settlement_plan_service=None):
        self.settlement_plan_service = (
            settlement_plan_service or SettlementPlanService()
        )

    def execute(self, user, plan_id):
        return self.settlement_plan_service.activate_plan(plan_id, user.sub)


class CancelSettlementPlanUseCase:
    def __init__(self, settlement_plan_service=None):
        self.settlement_plan_service = (
            settlement_plan_service or SettlementPlanService()
        )

    def execute(self, user, plan_id):
        return self.settlement_plan_service.cancel_plan(plan_id, user.sub)




class GetPlanItemPaymentOptionsUseCase:
    def __init__(self, settlement_plan_service=None):
        self.settlement_plan_service = (
            settlement_plan_service or SettlementPlanService()
        )

    def execute(self, user, item_id):
        return self.settlement_plan_service.get_plan_item_payment_options(
            item_id, user.sub
        )

class ReportPlanItemPaidUseCase:
    def __init__(self, settlement_plan_service=None):
        self.settlement_plan_service = (
            settlement_plan_service or SettlementPlanService()
        )

    def execute(self, user, item_id, payload):
        return self.settlement_plan_service.report_plan_item_paid(
            item_id,
            user.sub,
            description=payload.get("description"),
            payment_method=payload.get("payment_method"),
            paid_to_bank_card_id=payload.get("paid_to_bank_card_id"),
            amount_minor=payload.get("amount_minor"),
            paid_at=payload.get("paid_at"),
            note=payload.get("note"),
            tracking_code=payload.get("tracking_code"),
            receipt_file_id=payload.get("receipt_file_id"),
        )


class ConfirmPlanItemUseCase:
    def __init__(self, settlement_plan_service=None):
        self.settlement_plan_service = (
            settlement_plan_service or SettlementPlanService()
        )

    def execute(self, user, item_id):
        return self.settlement_plan_service.confirm_plan_item(item_id, user.sub)


class RejectPlanItemUseCase:
    def __init__(self, settlement_plan_service=None):
        self.settlement_plan_service = (
            settlement_plan_service or SettlementPlanService()
        )

    def execute(self, user, item_id, payload):
        return self.settlement_plan_service.reject_plan_item(
            item_id, user.sub, reason=payload.get("reason")
        )
