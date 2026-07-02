import { apiRequest, isApiError } from './api';

export type PaymentProvider = 'FAKE' | 'ZARINPAL';

// Backend contract: PaymentProviderChoices only accepts `FAKE` and `ZARINPAL`.
// The sandbox gateway URL returned by the backend is `https://sandbox.zarinpal.com/pg/StartPay/...`.
export const DEFAULT_WALLET_PAYMENT_PROVIDER: PaymentProvider = 'ZARINPAL';

export function normalizePaymentProvider(provider?: string | null): PaymentProvider {
  const normalized = String(provider || DEFAULT_WALLET_PAYMENT_PROVIDER)
    .trim()
    .toUpperCase()
    .replace(/[-\s]/g, '_');

  if (normalized === 'FAKE') return 'FAKE';

  // Accept older/typo values coming from old localStorage, URLs, or previous UI builds,
  // but always send the exact enum expected by wallet-service.
  if (['ZARINPAL', 'ZARIN_BAL', 'ZARINBAL', 'ZARIN_PAL'].includes(normalized)) {
    return 'ZARINPAL';
  }

  return DEFAULT_WALLET_PAYMENT_PROVIDER;
}

export function paymentProviderToApiValue(provider?: string | null) {
  return normalizePaymentProvider(provider);
}

export function getPaymentProviderApiValues(provider?: string | null) {
  return [paymentProviderToApiValue(provider)];
}

export function getPaymentRedirectUrl(intent: Partial<PaymentIntentResponse>) {
  return intent.payment_url || intent.redirect_url || intent.gateway_url || intent.url || '';
}


function uniquePayloads(payloads: Record<string, unknown>[]) {
  const seen = new Set<string>();
  return payloads.filter((payload) => {
    const key = JSON.stringify(payload);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}
export type PaymentIntentStatus = 'REDIRECT_REQUIRED' | 'SUCCEEDED' | 'FAILED' | 'EXPIRED' | 'RETRYABLE' | string;

export interface WalletInfo {
  id: string;
  currency: string;
  status: string;
  available_balance_minor: number;
  reserved_balance_minor: number;
  total_inflow_minor: number;
  total_outflow_minor: number;
  created_at?: string;
  updated_at?: string;
}

export interface WalletTransactionItem {
  id: string;
  type: string;
  status: string;
  direction: 'IN' | 'OUT' | string;
  amount_minor: number;
  currency: string;
  description?: string | null;
  reference_type?: string | null;
  reference_id?: string | null;
  created_at?: string;
  completed_at?: string | null;
}

export interface WalletSettlementSummaryItem {
  settlement_plan_item_id: string;
  plan_id: string;
  group_id: string;
  counterparty?: {
    user_id: string;
    art_name?: string | null;
  };
  amount_minor: number;
  currency: string;
  status: string;
  updated_at?: string;
}

export interface WalletSummaryResponse {
  wallet: WalletInfo;
  pending_receivables: WalletSettlementSummaryItem[];
  pending_payables: WalletSettlementSummaryItem[];
  recent_transactions: WalletTransactionItem[];
  pending_withdrawals?: unknown[];
  generated_at?: string;
}

export interface WalletTransactionListResponse {
  results: WalletTransactionItem[];
  next_cursor?: string | null;
}

export interface PaymentIntentResponse {
  payment_intent_id: string;
  purpose: 'WALLET_TOP_UP' | string;
  amount_minor: number;
  currency: string;
  provider: PaymentProvider;
  status: PaymentIntentStatus;
  payment_url?: string | null;
  redirect_url?: string | null;
  gateway_url?: string | null;
  url?: string | null;
  expires_at?: string;
  provider_reference?: string | null;
  created_at?: string;
  updated_at?: string;
  verified_at?: string | null;
  top_up_id?: string | null;
  wallet_transaction_id?: string | null;
  failure_reason?: string | null;
  provider_status?: string | null;
}

export interface PaymentIntentVerifyResponse {
  payment_intent_id: string;
  top_up_id?: string | null;
  wallet_transaction_id?: string | null;
  status: PaymentIntentStatus;
  amount_minor: number;
  currency: string;
  provider: PaymentProvider;
  provider_reference?: string | null;
  verified_at?: string | null;
  wallet_balance_minor: number;
  failure_reason?: string | null;
}

export interface WalletSettlementPayResponse {
  transaction_id: string;
  settlement_plan_item_id: string;
  status: string;
  amount_minor: number;
  currency: string;
  paid_at?: string;
}

export interface PendingWalletPayment {
  paymentIntentId: string;
  provider: PaymentProvider;
  amountMinor: number;
  settlementPlanItemId?: string;
  groupId?: string;
  walletPayIdempotencyKey?: string;
  createdAt: string;
}

const PENDING_WALLET_PAYMENT_KEY = 'hamdong_pending_wallet_payment';

export function createIdempotencyKey(prefix = 'wallet') {
  const randomPart =
    typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(16).slice(2)}`;

  return `${prefix}-${randomPart}`;
}

export function savePendingWalletPayment(payment: PendingWalletPayment) {
  localStorage.setItem(PENDING_WALLET_PAYMENT_KEY, JSON.stringify(payment));
}

export function getPendingWalletPayment() {
  const raw = localStorage.getItem(PENDING_WALLET_PAYMENT_KEY);
  if (!raw) return null;

  try {
    return JSON.parse(raw) as PendingWalletPayment;
  } catch {
    localStorage.removeItem(PENDING_WALLET_PAYMENT_KEY);
    return null;
  }
}

export function clearPendingWalletPayment() {
  localStorage.removeItem(PENDING_WALLET_PAYMENT_KEY);
}

export function getMyWallet() {
  return apiRequest<WalletInfo>('/wallets/me/');
}

export function getWalletSummary() {
  return apiRequest<WalletSummaryResponse>('/wallets/me/summary/');
}

export function listWalletTransactions(options: { pageSize?: number; cursor?: string } = {}) {
  const params = new URLSearchParams();
  if (options.pageSize) params.set('page_size', String(options.pageSize));
  if (options.cursor) params.set('cursor', options.cursor);
  const query = params.toString();

  return apiRequest<WalletTransactionListResponse>(`/wallets/me/transactions/${query ? `?${query}` : ''}`);
}

export async function createPaymentIntent(input: {
  amountMinor: number;
  provider?: PaymentProvider;
  idempotencyKey?: string;
}) {
  const provider = normalizePaymentProvider(input.provider);
  const idempotencyKey = input.idempotencyKey || createIdempotencyKey('top-up');

  return apiRequest<PaymentIntentResponse>('/payments/intents/', {
    method: 'POST',
    body: JSON.stringify({
      purpose: 'WALLET_TOP_UP',
      amount_minor: input.amountMinor,
      currency: 'IRR',
      provider,
      idempotency_key: idempotencyKey,
    }),
  });
}

export function getPaymentIntent(paymentIntentId: string) {
  return apiRequest<PaymentIntentResponse>(`/payments/intents/${paymentIntentId}/`);
}

export async function verifyPaymentIntent(input: {
  provider?: PaymentProvider;
  paymentIntentId: string;
  providerReference?: string | null;
}) {
  const provider = normalizePaymentProvider(input.provider);
  const providerApiValues = getPaymentProviderApiValues(provider);
  const reference = input.providerReference || undefined;
  const basePayload = { payment_intent_id: input.paymentIntentId };

  const payloads = uniquePayloads([
    {
      ...basePayload,
      ...(reference ? { provider_reference: reference, authority: reference } : {}),
    },
    {
      ...basePayload,
      ...(reference ? { provider_reference: reference } : {}),
    },
    {
      ...basePayload,
      ...(reference ? { authority: reference } : {}),
    },
    basePayload,
  ]);

  const providerPathValues = providerApiValues;
  let lastError: unknown;

  for (const providerPathValue of providerPathValues) {
    for (const body of payloads) {
      try {
        return await apiRequest<PaymentIntentVerifyResponse>(`/payments/gateway/${providerPathValue}/verify/`, {
          method: 'POST',
          body: JSON.stringify(body),
        });
      } catch (error) {
        lastError = error;

        if (!isApiError(error) || ![400, 404].includes(error.status)) {
          throw error;
        }
      }
    }
  }

  throw lastError;
}

export function paySettlementItemWithWallet(itemId: string, idempotencyKey = createIdempotencyKey('settlement-wallet-pay')) {
  return apiRequest<WalletSettlementPayResponse>(`/wallets/settlement-plan-items/${itemId}/pay/`, {
    method: 'POST',
    body: JSON.stringify({ idempotency_key: idempotencyKey }),
  });
}
