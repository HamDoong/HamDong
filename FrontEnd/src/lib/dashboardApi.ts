import { apiRequest } from './api';

export type DashboardActivityType =
  | 'GROUP_CREATED'
  | 'GROUP_MEMBER_JOINED'
  | 'GROUP_INVITATION_CREATED'
  | 'EXPENSE_CREATED'
  | 'EXPENSE_UPDATED'
  | 'EXPENSE_DELETED'
  | 'RECEIPT_UPLOADED'
  | 'SETTLEMENT_REPORTED'
  | 'SETTLEMENT_CONFIRMED'
  | 'SETTLEMENT_REJECTED'
  | 'SETTLEMENT_PLAN_ACTIVATED'
  | 'WALLET_PAYMENT_COMPLETED'
  | string;

export interface DashboardActivityItem {
  id: string;
  type: DashboardActivityType;
  group: {
    id: string;
    title?: string;
  };
  actor?: {
    user_id: string;
    art_name?: string | null;
  } | null;
  occurred_at: string;
  summary: Record<string, unknown>;
}

export interface DashboardActivityFeedResponse {
  results: DashboardActivityItem[];
  next_cursor?: string | null;
}

export type DashboardActionType =
  | 'PAY_DEBT'
  | 'CONFIRM_RECEIVED_PAYMENT'
  | 'REVIEW_REJECTED_PAYMENT'
  | 'RESPOND_TO_GROUP_INVITATION'
  | 'VIEW_IMPORTANT_NOTIFICATION'
  | string;

export type DashboardActionPriority = 'LOW' | 'MEDIUM' | 'HIGH' | string;

export interface DashboardActionReference {
  key: string;
  method: string;
  path: string;
}

export interface DashboardActionItem {
  id: string;
  type: DashboardActionType;
  priority: DashboardActionPriority;
  title: string;
  description: string;
  group?: {
    id: string;
    title?: string;
  } | null;
  source: {
    service: string;
    type: string;
    id: string;
  };
  amount_minor?: number | null;
  currency?: string | null;
  created_at?: string | null;
  due_at?: string | null;
  allowed_actions: DashboardActionReference[];
}

export interface DashboardActionItemsResponse {
  results: DashboardActionItem[];
  next_cursor?: string | null;
}

export interface DashboardActionItemsParams {
  type?: DashboardActionType;
  priority?: DashboardActionPriority;
  groupId?: string;
  cursor?: string;
  pageSize?: number;
}

function buildDashboardActionItemsQuery(params: DashboardActionItemsParams = {}) {
  const search = new URLSearchParams();

  if (params.type) search.set('type', params.type);
  if (params.priority) search.set('priority', params.priority);
  if (params.groupId) search.set('group_id', params.groupId);
  if (params.cursor) search.set('cursor', params.cursor);
  if (params.pageSize) search.set('page_size', String(params.pageSize));

  const query = search.toString();
  return query ? `?${query}` : '';
}

export async function getDashboardActionItems(params: DashboardActionItemsParams = {}) {
  const response = await apiRequest<DashboardActionItemsResponse>(
    `/dashboard/action-items/${buildDashboardActionItemsQuery(params)}`,
  );

  return response.results || [];
}

