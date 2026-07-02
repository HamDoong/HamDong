import { useEffect, useMemo, useState } from 'react';
import {
  ArrowLeft,
  CheckCircle2,
  CreditCard,
  History,
  Loader2,
  RefreshCw,
  WalletCards,
  X,
  type LucideIcon,
} from 'lucide-react';
import { MoneyWithWords } from '../lib/money';
import { getFriendlyApiErrorMessage, humanizeMachineLabel } from '../lib/userMessages';
import { useFeedback } from '../components/feedback/FeedbackProvider';
import {
  clearPendingWalletPayment,
  createIdempotencyKey,
  createPaymentIntent,
  getWalletSummary,
  savePendingWalletPayment,
  verifyPaymentIntent,
  type PaymentProvider,
  type WalletSummaryResponse,
  type WalletTransactionItem,
} from '../lib/walletApi';

interface WalletPageProps {
  onOpenActivities?: () => void;
  onOpenGroups?: () => void;
}

type TransactionTone = 'positive' | 'negative';

interface WalletTransactionView {
  id: string;
  title: string;
  description: string;
  amountMinor: number;
  statusLabel: string;
  dateLabel: string;
  tone: TransactionTone;
}

function normalizeDigits(value: string) {
  const persianDigits = '۰۱۲۳۴۵۶۷۸۹';
  const arabicDigits = '٠١٢٣٤٥٦٧٨٩';

  return value
    .replace(/[۰-۹]/g, (digit) => String(persianDigits.indexOf(digit)))
    .replace(/[٠-٩]/g, (digit) => String(arabicDigits.indexOf(digit)))
    .replace(/[,،\s]/g, '');
}

function parseAmountToMinor(value: string) {
  const normalized = normalizeDigits(value);
  const parsed = Number.parseInt(normalized, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
}

function formatMoney(amount: number) {
  const digits = Math.abs(Math.round(amount)).toLocaleString('fa-IR');
  return `تومان \u2066${digits}\u2069`;
}

function formatSignedMoney(amount: number) {
  const digits = Math.abs(Math.round(amount)).toLocaleString('fa-IR');
  const sign = amount > 0 ? '+' : amount < 0 ? '−' : '';
  return `تومان \u2066${sign}${digits}\u2069`;
}

function formatDate(value?: string | null) {
  if (!value) return 'زمان نامشخص';

  const timestamp = new Date(value).getTime();
  if (Number.isNaN(timestamp)) return 'زمان نامشخص';

  return new Intl.DateTimeFormat('fa-IR', {
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(timestamp));
}

function getWalletTransactionTitle(transaction: WalletTransactionItem) {
  const type = String(transaction.type || '').toUpperCase();

  if (type === 'TOP_UP') return 'شارژ کیف پول';
  if (type === 'SETTLEMENT_PAYMENT') return 'پرداخت بدهی با کیف پول';
  if (type === 'SETTLEMENT_RECEIVED') return 'دریافت تسویه در کیف پول';
  if (type === 'WITHDRAWAL') return 'برداشت از کیف پول';
  if (type === 'ADJUSTMENT') return 'اصلاح موجودی کیف پول';

  return humanizeMachineLabel(transaction.type, 'تراکنش کیف پول');
}

function mapWalletTransaction(transaction: WalletTransactionItem): WalletTransactionView {
  const isIncoming = String(transaction.direction || '').toUpperCase() === 'IN';
  const amountMinor = isIncoming ? transaction.amount_minor : -transaction.amount_minor;

  return {
    id: transaction.id,
    title: getWalletTransactionTitle(transaction),
    description: transaction.description || 'تراکنش کیف پول',
    amountMinor,
    statusLabel: humanizeMachineLabel(transaction.status, 'وضعیت نامشخص'),
    dateLabel: formatDate(transaction.completed_at || transaction.created_at),
    tone: isIncoming ? 'positive' : 'negative',
  };
}

function EmptyState({ icon: Icon, title, description }: { icon: LucideIcon; title: string; description: string }) {
  return (
    <div className="p-8 text-center">
      <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-200">
        <Icon className="h-6 w-6" />
      </div>
      <h3 className="text-base font-extrabold text-text dark:text-slate-100">{title}</h3>
      <p className="mx-auto mt-2 max-w-[360px] text-sm leading-7 text-muted dark:text-slate-400">{description}</p>
    </div>
  );
}

function TransactionRow({ transaction }: { transaction: WalletTransactionView }) {
  const isPositive = transaction.tone === 'positive';

  return (
    <div className="grid min-w-0 gap-3 border-b border-slate-100 px-4 py-3.5 last:border-b-0 sm:grid-cols-[minmax(0,1fr)_160px_120px] sm:items-center dark:border-slate-800">
      <div className="min-w-0 text-right">
        <p title={transaction.title} className="truncate text-sm font-black text-text dark:text-slate-100">{transaction.title}</p>
        <p title={transaction.description} className="mt-1 truncate text-xs font-semibold text-muted dark:text-slate-400">{transaction.description}</p>
      </div>

      <div className="min-w-0 text-right text-xs font-semibold text-muted dark:text-slate-400 sm:text-center">
        <p title={transaction.dateLabel} className="truncate">{transaction.dateLabel}</p>
        <p className="mt-1 truncate text-[10px]">{transaction.statusLabel}</p>
      </div>

      <p
        title={formatSignedMoney(transaction.amountMinor)}
        className={[
          'min-w-0 truncate text-left text-sm font-black',
          isPositive ? 'text-emerald-600 dark:text-emerald-200' : 'text-rose-500 dark:text-rose-200',
        ].join(' ')}
      >
        {formatSignedMoney(transaction.amountMinor)}
      </p>
    </div>
  );
}

export function WalletPage({ onOpenGroups }: WalletPageProps) {
  const { notify } = useFeedback();
  const [walletSummary, setWalletSummary] = useState<WalletSummaryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [topUpAmount, setTopUpAmount] = useState('');
  const [topUpProvider, setTopUpProvider] = useState<PaymentProvider>('FAKE');
  const [topUpLoading, setTopUpLoading] = useState(false);
  const [showTopUpModal, setShowTopUpModal] = useState(false);

  async function loadWalletData() {
    try {
      setLoading(true);
      setError(null);
      const nextSummary = await getWalletSummary();
      setWalletSummary(nextSummary);
    } catch (loadError) {
      console.error(loadError);
      setError('فعلاً نمی‌توانیم موجودی کیف پولت را نشان بدهیم. چند لحظه بعد دوباره امتحان کن.');
      setWalletSummary(null);
    } finally {
      setLoading(false);
    }
  }

  async function handleTopUpWallet() {
    const amountMinor = parseAmountToMinor(topUpAmount);

    if (amountMinor <= 0) {
      notify({
        type: 'error',
        title: 'مبلغ شارژ را اصلاح کن',
        description: 'برای شارژ کیف پول، یک مبلغ بیشتر از صفر وارد کن.',
      });
      return;
    }

    try {
      setTopUpLoading(true);
      const intent = await createPaymentIntent({
        amountMinor,
        provider: topUpProvider,
        idempotencyKey: createIdempotencyKey('wallet-top-up'),
      });

      savePendingWalletPayment({
        paymentIntentId: intent.payment_intent_id,
        provider: intent.provider,
        amountMinor,
        createdAt: new Date().toISOString(),
      });

      if (topUpProvider === 'FAKE') {
        const verifyResult = await verifyPaymentIntent({
          provider: 'FAKE',
          paymentIntentId: intent.payment_intent_id,
          providerReference: intent.provider_reference || intent.payment_intent_id,
        });

        if (String(verifyResult.status).toUpperCase() !== 'SUCCEEDED') {
          throw new Error(verifyResult.failure_reason || 'پرداخت آزمایشی تأیید نشد. دوباره امتحان کن.');
        }

        clearPendingWalletPayment();
        setTopUpAmount('');
        setShowTopUpModal(false);
        await loadWalletData();
        notify({
          type: 'success',
          title: 'کیف پولت شارژ شد',
          description: `${formatMoney(amountMinor)} به موجودی کیف پولت اضافه شد.`,
        });
        return;
      }

      window.location.href = intent.payment_url;
    } catch (topUpError) {
      console.error(topUpError);
      notify({
        type: 'error',
        title: 'شارژ کیف پول انجام نشد',
        description: getFriendlyApiErrorMessage(topUpError, { defaultMessage: 'پرداخت شروع نشد. مبلغ را بررسی کن و دوباره امتحان کن.' }),
      });
    } finally {
      setTopUpLoading(false);
    }
  }

  useEffect(() => {
    loadWalletData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const walletAvailableMinor = walletSummary?.wallet.available_balance_minor ?? 0;
  const walletReservedMinor = walletSummary?.wallet.reserved_balance_minor ?? 0;
  const transactions = useMemo(
    () => (walletSummary?.recent_transactions || []).map(mapWalletTransaction),
    [walletSummary],
  );

  return (
    <main dir="rtl" className="app-page text-right">
      <div className="app-container app-container-narrow space-y-5 sm:space-y-6">
        <section className="flex flex-col gap-3 rounded-[22px] border border-slate-200 bg-white/95 p-4 shadow-[0_14px_38px_rgba(15,23,42,0.055)] sm:flex-row sm:items-center sm:justify-between dark:border-slate-700 dark:bg-slate-950/90 dark:shadow-[0_18px_48px_rgba(0,0,0,0.22)]">
          <div>
            <h1 className="text-xl font-black text-text dark:text-slate-100">کیف پول</h1>
            <p className="mt-1 text-sm font-semibold leading-6 text-muted dark:text-slate-400">موجودی و تراکنش‌های کیف پول شما اینجا نمایش داده می‌شود.</p>
          </div>
          <button
            type="button"
            onClick={() => void loadWalletData()}
            disabled={loading}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-[14px] border border-emerald-300 bg-white px-4 text-sm font-black text-emerald-700 transition hover:bg-emerald-50 disabled:opacity-60 dark:border-emerald-500/35 dark:bg-slate-950 dark:text-emerald-200 dark:hover:bg-emerald-500/10"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            به‌روزرسانی
          </button>
        </section>

        {error ? <div className="rounded-[18px] border border-rose-200 bg-rose-50 p-4 text-center text-sm font-bold text-rose-600 dark:border-rose-500/25 dark:bg-rose-500/10 dark:text-rose-200">{error}</div> : null}

        <section className="wallet-balance-main relative overflow-hidden rounded-[24px] p-5 text-white sm:p-6">
          <div className="pointer-events-none absolute -left-20 -top-20 h-64 w-64 rounded-full bg-white/10 blur-3xl" />
          <div className="relative grid gap-5 md:grid-cols-[minmax(0,1fr)_auto] md:items-center">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="flex h-10 w-10 items-center justify-center rounded-full bg-white/12 ring-1 ring-white/15"><WalletCards className="h-5 w-5" /></span>
                <p className="text-sm font-black text-white/85">موجودی کیف پول</p>
                <span className="inline-flex items-center gap-1 rounded-full bg-white/12 px-3 py-1.5 text-xs font-black text-white ring-1 ring-white/15"><CheckCircle2 className="h-3.5 w-3.5" />قابل استفاده</span>
              </div>

              <div className="mt-4">
                {loading ? (
                  <span className="inline-flex items-center gap-2 text-2xl font-black"><Loader2 className="h-6 w-6 animate-spin" />در حال دریافت</span>
                ) : (
                  <MoneyWithWords amount={walletAvailableMinor} valueClassName="text-[34px] font-black tracking-[-0.04em] sm:text-[48px]" textClassName="mt-1 text-xs font-semibold text-white/70" showText={true} />
                )}
              </div>

              {walletReservedMinor > 0 ? (
                <p className="mt-3 text-xs font-semibold text-white/75">مبلغ رزروشده: <span className="font-black text-white">{formatMoney(walletReservedMinor)}</span></p>
              ) : null}
            </div>

            <div className="grid gap-2 sm:min-w-[190px]">
              <button
                type="button"
                onClick={() => setShowTopUpModal(true)}
                className="inline-flex h-12 items-center justify-center gap-2 rounded-[16px] bg-white px-5 text-sm font-black text-emerald-700 shadow-[0_14px_30px_rgba(15,23,42,0.14)] transition hover:bg-emerald-50"
              >
                <CreditCard className="h-4 w-4" />
                شارژ کیف پول
              </button>
              {onOpenGroups ? (
                <button
                  type="button"
                  onClick={onOpenGroups}
                  className="inline-flex h-11 items-center justify-center gap-2 rounded-[16px] border border-white/25 bg-white/10 px-5 text-xs font-black text-white transition hover:bg-white/15"
                >
                  تسویه بدهی‌ها
                  <ArrowLeft className="h-4 w-4" />
                </button>
              ) : null}
            </div>
          </div>
        </section>

        <section className="overflow-hidden rounded-[22px] border border-slate-200 bg-white shadow-[0_12px_34px_rgba(15,23,42,0.05)] dark:border-slate-700 dark:bg-slate-950/90">
          <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-4 py-4 dark:border-slate-800 sm:px-5">
            <div className="flex items-center gap-2">
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-200"><History className="h-4 w-4" /></span>
              <h2 className="text-lg font-black text-text dark:text-slate-100">تراکنش‌های کیف پول</h2>
            </div>
            <span className="text-xs font-bold text-muted dark:text-slate-400">{transactions.length.toLocaleString('fa-IR')} تراکنش اخیر</span>
          </div>

          {loading ? <EmptyState icon={Loader2} title="در حال دریافت تراکنش‌ها" description="تراکنش‌های کیف پول در حال آماده‌سازی است." /> : null}
          {!loading && transactions.length === 0 ? <EmptyState icon={WalletCards} title="تراکنشی برای نمایش نیست" description="بعد از شارژ کیف پول یا پرداخت بدهی با کیف پول، تراکنش‌ها اینجا نمایش داده می‌شوند." /> : null}
          {!loading && transactions.length > 0 ? <div>{transactions.map((transaction) => <TransactionRow key={transaction.id} transaction={transaction} />)}</div> : null}
        </section>
      </div>

      {showTopUpModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/55 px-4 py-6 backdrop-blur-sm" role="dialog" aria-modal="true">
          <div className="w-full max-w-[440px] rounded-[24px] border border-slate-200 bg-white p-4 shadow-[0_24px_70px_rgba(15,23,42,0.22)] dark:border-slate-700 dark:bg-slate-950">
            <div className="flex items-start justify-between gap-3 border-b border-slate-100 pb-4 dark:border-slate-800">
              <div>
                <h2 className="text-lg font-black text-text dark:text-slate-100">شارژ کیف پول</h2>
                <p className="mt-1 text-xs font-semibold leading-6 text-muted dark:text-slate-400">مبلغ شارژ را وارد کن و روش پرداخت را انتخاب کن.</p>
              </div>
              <button
                type="button"
                onClick={() => setShowTopUpModal(false)}
                className="flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 text-slate-500 transition hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-900"
                aria-label="بستن"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="grid gap-3 py-4">
              <label className="grid gap-2 text-sm font-black text-text dark:text-slate-100">
                مبلغ شارژ
                <input
                  dir="rtl"
                  inputMode="numeric"
                  value={topUpAmount}
                  onChange={(event) => setTopUpAmount(event.target.value)}
                  placeholder="مثلاً ۵۰۰۰۰۰"
                  className="h-12 rounded-[16px] border border-emerald-200 bg-white px-3 text-right text-sm font-bold outline-none transition focus:border-emerald-400 focus:ring-4 focus:ring-emerald-500/10 dark:border-emerald-500/20 dark:bg-slate-900 dark:text-slate-100"
                />
              </label>

              <label className="grid gap-2 text-sm font-black text-text dark:text-slate-100">
                روش پرداخت
                <select
                  value={topUpProvider}
                  onChange={(event) => setTopUpProvider(event.target.value as PaymentProvider)}
                  className="h-12 rounded-[16px] border border-emerald-200 bg-white px-3 text-sm font-black outline-none transition focus:border-emerald-400 focus:ring-4 focus:ring-emerald-500/10 dark:border-emerald-500/20 dark:bg-slate-900 dark:text-slate-100"
                >
                  <option value="FAKE">درگاه آزمایشی</option>
                  <option value="ZARINPAL">زرین‌پال</option>
                </select>
              </label>
            </div>

            <div className="grid gap-2 sm:grid-cols-2">
              <button
                type="button"
                onClick={() => setShowTopUpModal(false)}
                disabled={topUpLoading}
                className="h-11 rounded-[15px] border border-slate-200 text-sm font-black text-slate-700 transition hover:bg-slate-50 disabled:opacity-60 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-900"
              >
                انصراف
              </button>
              <button
                type="button"
                onClick={() => void handleTopUpWallet()}
                disabled={topUpLoading}
                className="inline-flex h-11 items-center justify-center gap-2 rounded-[15px] bg-emerald-600 text-sm font-black text-white transition hover:bg-emerald-700 disabled:opacity-70 dark:bg-emerald-500 dark:hover:bg-emerald-400"
              >
                {topUpLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <CreditCard className="h-4 w-4" />}
                شارژ کیف پول
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}
