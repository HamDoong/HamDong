import { apiRequest } from './api';

export type SettlementStatus =
  | 'PENDING'
  | 'PENDING_CONFIRMATION'
  | 'REPORTED'
  | 'CONFIRMED'
  | 'REJECTED'
  | 'CANCELLED'
  | 'ACTIVE'
  | 'DRAFT'
  | 'COMPLETED'
  | 'EXPIRED'
  | string;

export interface BalanceItem {
  user_id: string;
  art_name?: string;
  display_name?: string;
  email?: string;
  phone_number?: string;
  net_balance_minor: number;
  status?: string;
}

export interface GroupBalancesResponse {
  group_id: string;
  currency: string;
  balances: BalanceItem[];
  calculated_at?: string;
}

export interface MyBalanceResponse {
  group_id: string;
  user_id: string;
  currency: string;
  net_balance_minor: number;
  status?: string;
}

export interface DebtItem {
  id: string;
  source_expense_id?: string;
  debtor_user_id: string;
  creditor_user_id: string;
  amount_minor: number;
  currency?: string;
  status?: SettlementStatus;
  entry_type?: string;
}

export interface GroupDebtsResponse {
  group_id: string;
  currency: string;
  debts: DebtItem[];
}

export interface SettlementPlanItem {
  id: string;
  payer_user_id: string;
  payer_art_name?: string | null;
  payer_display_name?: string;
  receiver_user_id: string;
  receiver_art_name?: string | null;
  receiver_display_name?: string;
  amount_minor: number;
  status?: SettlementStatus;
  order_index?: number;
  manual_settlement_id?: string | null;
}

export interface SettlementPlan {
  id: string;
  group_id: string;
  currency: string;
  status?: SettlementStatus;
  total_debt_minor?: number;
  transaction_count?: number;
  source_balance_calculated_at?: string;
  created_at?: string;
  updated_at?: string;
  items: SettlementPlanItem[];
}

export interface SettlementItem {
  id: string;
  group_id: string;
  payer_user_id: string;
  receiver_user_id: string;
  amount_minor: number;
  currency: string;
  status?: SettlementStatus;
  description?: string;
  created_at?: string;
}

export interface GroupSettlementsResponse {
  group_id: string;
  settlements: SettlementItem[];
}

export interface SettlementMessageResponse {
  message?: string;
  manual_settlement_id?: string;
}

export interface CreateSettlementInput {
  receiver_user_id: string;
  amount_minor: number;
  currency?: string;
  description?: string;
}

function unwrapList<T>(data: T[] | { results?: T[]; data?: T[]; settlements?: T[] }) {
  if (Array.isArray(data)) return data;
  return data.results || data.data || data.settlements || [];
}

function normalizeSettlementPlan(plan: SettlementPlan): SettlementPlan {
  return {
    ...plan,
    items: (plan.items || []).map((item) => ({
      ...item,
      payer_display_name: item.payer_display_name || item.payer_art_name || undefined,
      receiver_display_name: item.receiver_display_name || item.receiver_art_name || undefined,
    })),
  };
}

export async function getGroupBalances(groupId: string) {
  return apiRequest<GroupBalancesResponse>(`/groups/${groupId}/balances/`);
}

export async function getMyGroupBalance(groupId: string) {
  return apiRequest<MyBalanceResponse>(`/groups/${groupId}/balances/me/`);
}

export async function getGroupDebts(groupId: string) {
  return apiRequest<GroupDebtsResponse>(`/groups/${groupId}/debts/`);
}

export async function getSettlementPlan(groupId: string) {
  const plan = await apiRequest<SettlementPlan>(`/groups/${groupId}/settlement-plan/`);
  return normalizeSettlementPlan(plan);
}

export async function generateSettlementPlan(groupId: string) {
  const plan = await apiRequest<SettlementPlan>(`/groups/${groupId}/settlement-plan/generate/`, {
    method: 'POST',
  });

  return normalizeSettlementPlan(plan);
}

export async function listGroupSettlements(groupId: string) {
  const data = await apiRequest<GroupSettlementsResponse | SettlementItem[] | { results?: SettlementItem[]; data?: SettlementItem[] }>(
    `/groups/${groupId}/settlements/`,
  );

  if (!Array.isArray(data) && 'settlements' in data) {
    return data.settlements;
  }

  return unwrapList(data);
}

export async function createGroupSettlement(groupId: string, input: CreateSettlementInput) {
  return apiRequest<SettlementItem>(`/groups/${groupId}/settlements/`, {
    method: 'POST',
    body: JSON.stringify({
      receiver_user_id: input.receiver_user_id,
      amount_minor: input.amount_minor,
      currency: input.currency || 'IRR',
      description: input.description || '',
    }),
  });
}

export async function activateSettlementPlan(planId: string) {
  return apiRequest<SettlementMessageResponse>(`/settlement-plans/${planId}/activate/`, {
    method: 'POST',
  });
}

export async function cancelSettlementPlan(planId: string) {
  return apiRequest<SettlementMessageResponse>(`/settlement-plans/${planId}/cancel/`, {
    method: 'POST',
  });
}

export async function reportPlanItemPaid(itemId: string, description = '') {
  return apiRequest<SettlementMessageResponse>(`/settlement-plan-items/${itemId}/report-paid/`, {
    method: 'POST',
    body: JSON.stringify({ description }),
  });
}

export async function confirmPlanItem(itemId: string) {
  return apiRequest<SettlementMessageResponse>(`/settlement-plan-items/${itemId}/confirm/`, {
    method: 'POST',
  });
}

export async function rejectPlanItem(itemId: string, reason = '') {
  return apiRequest<SettlementMessageResponse>(`/settlement-plan-items/${itemId}/reject/`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}

export async function confirmSettlement(settlementId: string) {
  return apiRequest<SettlementMessageResponse>(`/settlements/${settlementId}/confirm/`, {
    method: 'POST',
  });
}

export async function rejectSettlement(settlementId: string, reason = '') {
  return apiRequest<SettlementMessageResponse>(`/settlements/${settlementId}/reject/`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}

export async function cancelSettlement(settlementId: string) {
  return apiRequest<SettlementMessageResponse>(`/settlements/${settlementId}/cancel/`, {
    method: 'POST',
  });
}
