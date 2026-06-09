import { apiRequest } from './api';

export type ExpenseSplitMethod = 'EQUAL' | 'CUSTOM';
export type ExpenseStatus = 'ACTIVE' | 'DELETED' | 'CANCELLED' | string;
export type FeeType = 'NONE' | 'PERCENTAGE' | 'AMOUNT' | string;

export interface ExpenseParticipant {
  user_id: string;
  phone_number?: string;
  display_name_snapshot?: string;
  base_share_minor?: number;
  tax_share_minor?: number;
  service_fee_share_minor?: number;
  total_share_minor?: number;
  is_included?: boolean;
}

export interface BackendExpense {
  id: string;
  group_id: string;
  title: string;
  description?: string;
  payer_user_id: string;
  created_by_user_id?: string;
  currency?: string;
  base_amount_minor: number;
  tax_amount_minor?: number;
  service_fee_amount_minor?: number;
  total_amount_minor?: number;
  split_method?: ExpenseSplitMethod | string;
  status?: ExpenseStatus;
  participants?: ExpenseParticipant[];
  created_at?: string;
  updated_at?: string;
  expense_date?: string;
  receipt_file_id?: string;
  receipt_url?: string;
}

export interface ExpenseParticipantInput {
  user_id: string;
  base_share_minor: number;
}

export interface CreateExpenseInput {
  title: string;
  description?: string;
  payer_user_id: string;
  base_amount_minor: number;
  currency?: string;
  split_method?: ExpenseSplitMethod;
  participant_user_ids?: string[];
  participants?: ExpenseParticipantInput[];
  tax_type?: FeeType;
  tax_percentage?: string;
  tax_amount_minor?: number;
  service_fee_type?: FeeType;
  service_fee_percentage?: string;
  service_fee_amount_minor?: number;
  expense_date?: string;
  receipt_file_id?: string;
  receipt_url?: string;
}

export interface UpdateExpenseInput extends Partial<CreateExpenseInput> {}

export interface ListGroupExpensesFilters {
  created_by_user_id?: string;
  from_date?: string;
  page?: number;
  page_size?: number;
  payer_user_id?: string;
  to_date?: string;
}

function unwrapList<T>(data: T[] | { results?: T[]; data?: T[]; items?: T[] }) {
  if (Array.isArray(data)) return data;
  return data.results || data.data || data.items || [];
}

function buildQuery(filters: ListGroupExpensesFilters = {}) {
  const params = new URLSearchParams();

  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      params.set(key, String(value));
    }
  });

  const query = params.toString();
  return query ? `?${query}` : '';
}

export async function listGroupExpenses(
  groupId: string,
  filters: ListGroupExpensesFilters = {},
) {
  const normalizedFilters = { ...filters };

  // Some backend versions reject pagination query params for this endpoint.
  // Keep date/user filters, but do not force page_size unless the caller really needs it.
  if (normalizedFilters.page_size === undefined) {
    delete normalizedFilters.page_size;
  }

  const path = `/groups/${groupId}/expenses/${buildQuery(normalizedFilters)}`;

  try {
    const data = await apiRequest<
      BackendExpense[] | { results?: BackendExpense[]; data?: BackendExpense[]; items?: BackendExpense[] }
    >(path);

    return unwrapList(data);
  } catch (error) {
    const hasQuery = buildQuery(normalizedFilters).length > 0;

    // Fallback for strict/older expense-service builds: retry without query params.
    if (hasQuery) {
      try {
        const data = await apiRequest<
          BackendExpense[] | { results?: BackendExpense[]; data?: BackendExpense[]; items?: BackendExpense[] }
        >(`/groups/${groupId}/expenses/`);

        return unwrapList(data);
      } catch (fallbackError) {
        console.warn('Expense list request failed without query params too:', fallbackError);
        return [];
      }
    }

    console.warn('Expense list request failed and was ignored for this group:', error);
    return [];
  }
}

export async function createGroupExpense(groupId: string, input: CreateExpenseInput) {
  return apiRequest<BackendExpense>(`/groups/${groupId}/expenses/`, {
    method: 'POST',
    body: JSON.stringify({
      title: input.title.trim(),
      description: input.description?.trim() || '',
      payer_user_id: input.payer_user_id,
      base_amount_minor: input.base_amount_minor,
      currency: input.currency || 'IRR',
      split_method: input.split_method || 'EQUAL',
      participant_user_ids: input.participant_user_ids,
      participants: input.participants,
      tax_type: input.tax_type || 'NONE',
      tax_percentage: input.tax_percentage,
      tax_amount_minor: input.tax_amount_minor ?? 0,
      service_fee_type: input.service_fee_type || 'NONE',
      service_fee_percentage: input.service_fee_percentage,
      service_fee_amount_minor: input.service_fee_amount_minor ?? 0,
      expense_date: input.expense_date,
      receipt_file_id: input.receipt_file_id,
      receipt_url: input.receipt_url,
    }),
  });
}

export async function getExpenseDetail(expenseId: string) {
  return apiRequest<BackendExpense>(`/expenses/${expenseId}/`);
}

export async function updateExpense(expenseId: string, input: UpdateExpenseInput) {
  return apiRequest<BackendExpense>(`/expenses/${expenseId}/`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  });
}

export async function deleteExpense(expenseId: string) {
  return apiRequest<{ message?: string; status?: string }>(`/expenses/${expenseId}/`, {
    method: 'DELETE',
  });
}
