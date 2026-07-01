import { API_BASE_URL, apiRequest, isApiError, normalizeApiBaseUrl, type ApiRequestOptions } from './api';

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

export interface SettlementReminderResponse {
  reminder_id: string;
  status: string;
  channels: string[];
}

export interface GroupReminderSettings {
  group_id: string;
  is_enabled: boolean;
  first_reminder_after_hours: number;
  repeat_interval_hours: number;
  maximum_reminders: number;
  send_in_app: boolean;
  send_email: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

export type UpdateGroupReminderSettingsInput = Partial<Pick<
  GroupReminderSettings,
  | 'is_enabled'
  | 'first_reminder_after_hours'
  | 'repeat_interval_hours'
  | 'maximum_reminders'
  | 'send_in_app'
  | 'send_email'
>>;

export interface RunGroupRemindersResponse {
  eligible_count: number;
  created_count: number;
  skipped_count: number;
  skip_reasons?: Record<string, number>;
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

const DEFAULT_LOCAL_SETTLEMENT_API_BASE_URL = 'http://localhost:8004/api/v1';

function getSettlementFallbackBaseUrl() {
  const configuredBaseUrl = import.meta.env.VITE_SETTLEMENT_API_BASE_URL?.trim();

  if (configuredBaseUrl) {
    return normalizeApiBaseUrl(configuredBaseUrl);
  }

  if (typeof window !== 'undefined' && ['localhost', '127.0.0.1'].includes(window.location.hostname)) {
    return DEFAULT_LOCAL_SETTLEMENT_API_BASE_URL;
  }

  return undefined;
}

async function settlementReminderApiRequest<T>(path: string, options: ApiRequestOptions = {}) {
  try {
    return await apiRequest<T>(path, options);
  } catch (error) {
    const fallbackBaseUrl = getSettlementFallbackBaseUrl();
    const gatewayRouteMissing = isApiError(error) && [404, 500, 502, 503, 504].includes(error.status);

    if (
      !fallbackBaseUrl ||
      normalizeApiBaseUrl(options.baseUrl || API_BASE_URL) === fallbackBaseUrl ||
      (!gatewayRouteMissing && !(error instanceof TypeError))
    ) {
      throw error;
    }

    return apiRequest<T>(path, {
      ...options,
      baseUrl: fallbackBaseUrl,
    });
  }
}

export async function getGroupReminderSettings(groupId: string) {
  return settlementReminderApiRequest<GroupReminderSettings>(`/groups/${groupId}/reminder-settings/`);
}

export async function updateGroupReminderSettings(
  groupId: string,
  input: UpdateGroupReminderSettingsInput,
) {
  return settlementReminderApiRequest<GroupReminderSettings>(`/groups/${groupId}/reminder-settings/`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  });
}

export async function runGroupReminders(groupId: string, dryRun = false) {
  return settlementReminderApiRequest<RunGroupRemindersResponse>(`/groups/${groupId}/reminders/run/`, {
    method: 'POST',
    body: JSON.stringify({ dry_run: dryRun }),
  });
}

export async function sendPlanItemReminder(
  itemId: string,
  options: { send_in_app?: boolean; send_email?: boolean } = {},
) {
  return apiRequest<SettlementReminderResponse>(`/settlement-plan-items/${itemId}/reminders/send/`, {
    method: 'POST',
    body: JSON.stringify({
      send_in_app: options.send_in_app ?? true,
      send_email: options.send_email ?? false,
    }),
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
