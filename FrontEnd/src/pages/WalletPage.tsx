import { useEffect, useMemo, useState } from 'react';
import {
  AlertCircle,
  ArrowDown,
  ArrowUp,
  CheckCircle2,
  ChevronLeft,
  Clock3,
  CreditCard,
  History,
  Loader2,
  Plus,
  ReceiptText,
  RefreshCw,
  Send,
  Users,
  WalletCards,
  type LucideIcon,
} from 'lucide-react';
import { listGroupExpenses, type BackendExpense, type ExpenseParticipant } from '../lib/expenseApi';
import { getGroupBalances, getMyGroupBalance, getSettlementPlan, listGroupSettlements, type BalanceItem, type SettlementItem, type SettlementPlanItem } from '../lib/settlementApi';
import { getMyGroups, type BackendGroup } from '../lib/groupApi';
import { getCurrentUser } from '../lib/userApi';
import { humanizeMachineLabel } from '../lib/userMessages';

type TransactionTone = 'positive' | 'negative';
type TransactionStatus = 'received' | 'paid' | 'pending';

interface WalletPageProps {
  onOpenActivities?: () => void;
  onOpenGroups?: () => void;
}

interface WalletTransaction {
  id: string;
  title: string;
  subtitle: string;
  time: string;
  amount: number;
  status: TransactionStatus;
  statusLabel: string;
  tone: TransactionTone;
  avatar: string;
  avatarClassName: string;
  icon: LucideIcon;
  createdAt: number;
}

interface WalletSummary {
  creditMinor: number;
  debtMinor: number;
  netMinor: number;
  openSettlementMinor: number;
  activeGroupCount: number;
  settlementCount: number;
  expenseCount: number;
}

interface WalletGroupBalance {
  groupId: string;
  groupTitle: string;
  netMinor: number;
}

interface SettlementSuggestion {
  id: string;
  groupTitle: string;
  personName: string;
  description: string;
  amountMinor: number;
  tone: TransactionTone;
  statusLabel: string;
}

interface GroupWalletData {
  group: BackendGroup;
  myBalance: number;
  balances: BalanceItem[];
  settlements: SettlementItem[];
  expenses: BackendExpense[];
  planItems: SettlementPlanItem[];
}

const emptySummary: WalletSummary = {
  creditMinor: 0,
  debtMinor: 0,
  netMinor: 0,
  openSettlementMinor: 0,
  activeGroupCount: 0,
  settlementCount: 0,
  expenseCount: 0,
};

const avatarGradients = [
  'from-emerald-300 to-teal-700',
  'from-sky-300 to-cyan-700',
  'from-rose-300 to-pink-600',
  'from-amber-300 to-orange-600',
  'from-violet-300 to-indigo-700',
  'from-slate-400 to-slate-700',
];

function settledValue<T>(result: PromiseSettledResult<T>, fallback: T) {
  return result.status === 'fulfilled' ? result.value : fallback;
}

function isActiveGroup(group: BackendGroup) {
  return group.status !== 'ARCHIVED';
}

function getGroupTitle(group?: BackendGroup) {
  return group?.title || 'گروه بدون عنوان';
}

function getDateTimestamp(value?: string | null) {
  if (!value) return 0;

  const timestamp = new Date(value).getTime();
  return Number.isNaN(timestamp) ? 0 : timestamp;
}

function formatDate(value?: string | null) {
  const timestamp = getDateTimestamp(value);

  if (!timestamp) return 'زمان نامشخص';

  return new Intl.DateTimeFormat('fa-IR', {
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(timestamp));
}

function formatMoney(amount: number) {
  return `${Math.abs(Math.round(amount)).toLocaleString('fa-IR')} تومان`;
}

function formatSignedMoney(amount: number) {
  const sign = amount > 0 ? '+' : amount < 0 ? '-' : '';
  return `${sign}${formatMoney(amount)}`;
}

function getAvatarText(value: string) {
  return value.trim().slice(0, 1) || '؟';
}

function getAvatarClassName(seed: string) {
  const hash = Array.from(seed).reduce((sum, char) => sum + char.charCodeAt(0), 0);
  return avatarGradients[hash % avatarGradients.length];
}

function getExpenseTotal(expense: BackendExpense) {
  return (
    expense.total_amount_minor ??
    (expense.base_amount_minor || 0) +
      (expense.tax_amount_minor || 0) +
      (expense.service_fee_amount_minor || 0)
  );
}

function getParticipantShare(participant?: ExpenseParticipant) {
  if (!participant) return 0;

  return (
    participant.total_share_minor ??
    (participant.base_share_minor || 0) +
      (participant.tax_share_minor || 0) +
      (participant.service_fee_share_minor || 0)
  );
}

function isOpenStatus(status?: string) {
  const value = (status || '').toUpperCase();
  return value !== 'CONFIRMED' && value !== 'CANCELLED' && value !== 'COMPLETED';
}

function getSettlementStatusLabel(status?: string) {
  const value = (status || '').toUpperCase();

  if (value === 'CONFIRMED') return 'تایید شده';
  if (value === 'PENDING_CONFIRMATION') return 'در انتظار تایید';
  if (value === 'REPORTED') return 'گزارش پرداخت';
  if (value === 'REJECTED') return 'رد شده';
  if (value === 'CANCELLED') return 'لغو شده';
  if (value === 'PENDING') return 'در انتظار';

  return humanizeMachineLabel(status, 'وضعیت نامشخص');
}

function getNameMap(balances: BalanceItem[]) {
  return new Map(
    balances.map((item) => [
      item.user_id,
      item.display_name || item.art_name || item.email || item.phone_number || `کاربر ${item.user_id.slice(0, 8)}`,
    ]),
  );
}

function getUserName(userId: string, nameMap: Map<string, string>) {
  return nameMap.get(userId) || `کاربر ${userId.slice(0, 8)}`;
}

function buildSettlementTransaction(
  settlement: SettlementItem,
  group: BackendGroup,
  currentUserId: string | null,
  nameMap: Map<string, string>,
): WalletTransaction | null {
  const isPayer = currentUserId ? settlement.payer_user_id === currentUserId : false;
  const isReceiver = currentUserId ? settlement.receiver_user_id === currentUserId : false;

  if (currentUserId && !isPayer && !isReceiver) return null;

  const amount = isPayer ? -settlement.amount_minor : settlement.amount_minor;
  const otherUserId = isPayer ? settlement.receiver_user_id : settlement.payer_user_id;
  const otherName = getUserName(otherUserId, nameMap);
  const title = isPayer ? `پرداخت تسویه به ${otherName}` : `دریافت تسویه از ${otherName}`;
  const createdAt = getDateTimestamp(settlement.created_at);

  return {
    id: `settlement-${settlement.id}`,
    title,
    subtitle: `گروه «${getGroupTitle(group)}»`,
    time: formatDate(settlement.created_at),
    amount,
    status: amount >= 0 ? 'received' : 'paid',
    statusLabel: getSettlementStatusLabel(settlement.status),
    tone: amount >= 0 ? 'positive' : 'negative',
    avatar: getAvatarText(otherName),
    avatarClassName: getAvatarClassName(otherName),
    icon: CreditCard,
    createdAt,
  };
}

function buildExpenseTransaction(
  expense: BackendExpense,
  group: BackendGroup,
  currentUserId: string | null,
): WalletTransaction | null {
  if (expense.status === 'DELETED' || expense.status === 'CANCELLED') return null;

  const total = getExpenseTotal(expense);
  const participant = currentUserId
    ? expense.participants?.find((item) => item.user_id === currentUserId)
    : undefined;
  const share = getParticipantShare(participant);
  const isPayer = currentUserId ? expense.payer_user_id === currentUserId : false;
  const amount = isPayer ? Math.max(total - share, total || share) : -(share || total);
  const createdAt = getDateTimestamp(expense.expense_date || expense.created_at);
  const title = isPayer ? `پرداخت هزینه «${expense.title}»` : `سهم شما از «${expense.title}»`;

  if (!amount) return null;

  return {
    id: `expense-${expense.id}`,
    title,
    subtitle: `گروه «${getGroupTitle(group)}»`,
    time: formatDate(expense.expense_date || expense.created_at),
    amount,
    status: amount >= 0 ? 'received' : 'paid',
    statusLabel: isPayer ? 'هزینه ثبت‌شده' : 'سهم هزینه',
    tone: amount >= 0 ? 'positive' : 'negative',
    avatar: getAvatarText(expense.title),
    avatarClassName: getAvatarClassName(expense.title),
    icon: ReceiptText,
    createdAt,
  };
}

function buildSettlementSuggestion(
  item: SettlementPlanItem,
  group: BackendGroup,
  currentUserId: string | null,
): SettlementSuggestion | null {
  if (!isOpenStatus(item.status)) return null;

  const isPayer = currentUserId ? item.payer_user_id === currentUserId : false;
  const isReceiver = currentUserId ? item.receiver_user_id === currentUserId : false;

  if (currentUserId && !isPayer && !isReceiver) return null;

  const payerName = item.payer_display_name || item.payer_art_name || 'پرداخت‌کننده';
  const receiverName = item.receiver_display_name || item.receiver_art_name || 'دریافت‌کننده';
  const personName = isPayer ? receiverName : isReceiver ? payerName : `${payerName} به ${receiverName}`;

  return {
    id: `plan-item-${item.id}`,
    groupTitle: getGroupTitle(group),
    personName,
    description: isPayer ? 'پرداخت پیشنهادی' : 'دریافت پیشنهادی',
    amountMinor: item.amount_minor,
    tone: isPayer ? 'negative' : 'positive',
    statusLabel: getSettlementStatusLabel(item.status),
  };
}

function ActionButton({
  icon: Icon,
  label,
  onClick,
  loading = false,
}: {
  icon: LucideIcon;
  label: string;
  onClick?: () => void;
  loading?: boolean;
}) {
  const ButtonIcon = loading ? Loader2 : Icon;

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={loading}
      className="group flex h-[72px] items-center justify-center gap-3 rounded-3xl border border-border bg-white px-5 text-base font-bold text-text shadow-sm transition hover:-translate-y-0.5 hover:border-emerald-200 hover:shadow-[0_18px_45px_rgba(15,23,42,0.07)] disabled:cursor-not-allowed disabled:opacity-70"
    >
      <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600 transition group-hover:bg-emerald-600 group-hover:text-white">
        <ButtonIcon className={['h-5.5 w-5.5', loading ? 'animate-spin' : ''].join(' ')} />
      </span>
      {label}
    </button>
  );
}

function TransactionRow({ transaction }: { transaction: WalletTransaction }) {
  const isPositive = transaction.tone === 'positive';
  const DirectionIcon = isPositive ? ArrowDown : ArrowUp;
  const Icon = transaction.icon;

  return (
    <div className="grid grid-cols-[minmax(92px,150px)_minmax(0,1fr)] items-center gap-4 border-b border-border px-5 py-4 last:border-b-0 md:grid-cols-[minmax(120px,180px)_minmax(110px,150px)_minmax(0,1fr)]">
      <div className="text-left">
        <div
          className={[
            'text-lg font-extrabold tracking-normal',
            isPositive ? 'text-emerald-600' : 'text-rose-500',
          ].join(' ')}
        >
          {formatSignedMoney(transaction.amount)}
        </div>
      </div>

      <div className="hidden md:flex md:justify-center">
        <span
          className={[
            'inline-flex h-8 items-center justify-center rounded-xl px-4 text-xs font-bold',
            transaction.status === 'received'
              ? 'bg-emerald-50 text-emerald-600'
              : transaction.status === 'paid'
                ? 'bg-rose-50 text-rose-500'
                : 'bg-amber-50 text-amber-600',
          ].join(' ')}
        >
          {transaction.statusLabel}
        </span>
      </div>

      <div className="flex min-w-0 items-center justify-end gap-4">
        <div className="min-w-0 text-right">
          <div className="truncate text-base font-bold text-text">{transaction.title}</div>
          <div className="mt-1 truncate text-sm text-muted">{transaction.subtitle}</div>
        </div>

        <div
          className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-gradient-to-br ${transaction.avatarClassName} text-sm font-bold text-white`}
        >
          {transaction.avatar}
        </div>

        <div className="hidden w-24 shrink-0 text-center text-sm text-muted sm:block">
          {transaction.time}
        </div>

        <div
          className={[
            'flex h-11 w-11 shrink-0 items-center justify-center rounded-full',
            isPositive ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-500',
          ].join(' ')}
        >
          <DirectionIcon className="h-5 w-5" />
        </div>

        <div className="hidden h-11 w-11 shrink-0 items-center justify-center rounded-full bg-slate-50 text-slate-500 xl:flex">
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}

function SummaryRow({
  label,
  value,
  tone = 'neutral',
}: {
  label: string;
  value: string;
  tone?: 'positive' | 'negative' | 'neutral';
}) {
  return (
    <div className="flex items-center justify-between gap-4 text-sm">
      <span className="text-muted">{label}</span>
      <span
        className={[
          'font-extrabold tracking-normal',
          tone === 'positive' ? 'text-emerald-600' : '',
          tone === 'negative' ? 'text-rose-500' : '',
          tone === 'neutral' ? 'text-text' : '',
        ].join(' ')}
      >
        {value}
      </span>
    </div>
  );
}

function QuickAction({ icon: Icon, label, onClick }: { icon: LucideIcon; label: string; onClick?: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full items-center justify-between border-b border-border py-4 text-right text-sm font-semibold text-slate-700 transition last:border-b-0 hover:text-emerald-600"
    >
      <ChevronLeft className="h-4.5 w-4.5 text-slate-400" />
      <span className="flex items-center gap-3">
        {label}
        <Icon className="h-5 w-5 text-slate-500" />
      </span>
    </button>
  );
}

function EmptyState({
  icon: Icon,
  title,
  description,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
}) {
  return (
    <div className="p-8 text-center">
      <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600">
        <Icon className="h-6 w-6" />
      </div>
      <h3 className="text-base font-extrabold text-text">{title}</h3>
      <p className="mx-auto mt-2 max-w-[360px] text-sm leading-7 text-muted">{description}</p>
    </div>
  );
}

function SettlementSuggestionRow({ item }: { item: SettlementSuggestion }) {
  const isPositive = item.tone === 'positive';

  return (
    <div className="flex items-center justify-between gap-4 border-b border-border py-4 last:border-b-0">
      <div className="text-left">
        <div className={['text-sm font-black', isPositive ? 'text-emerald-600' : 'text-rose-500'].join(' ')}>
          {formatMoney(item.amountMinor)}
        </div>
        <div className="mt-1 text-xs text-muted">{item.statusLabel}</div>
      </div>
      <div className="min-w-0 text-right">
        <div className="truncate text-sm font-bold text-text">{item.personName}</div>
        <div className="mt-1 truncate text-xs text-muted">
          {item.description} در «{item.groupTitle}»
        </div>
      </div>
    </div>
  );
}

function GroupBalanceRow({ item }: { item: WalletGroupBalance }) {
  const isPositive = item.netMinor >= 0;

  return (
    <div className="flex items-center justify-between gap-4 border-b border-border py-4 last:border-b-0">
      <div className={['text-sm font-black', isPositive ? 'text-emerald-600' : 'text-rose-500'].join(' ')}>
        {formatSignedMoney(item.netMinor)}
      </div>
      <div className="min-w-0 text-right">
        <div className="truncate text-sm font-bold text-text">{item.groupTitle}</div>
        <div className="mt-1 text-xs text-muted">
          {isPositive ? 'طلب شما در این گروه' : 'بدهی شما در این گروه'}
        </div>
      </div>
    </div>
  );
}

export function WalletPage({ onOpenActivities, onOpenGroups }: WalletPageProps) {
  const [summary, setSummary] = useState<WalletSummary>(emptySummary);
  const [transactions, setTransactions] = useState<WalletTransaction[]>([]);
  const [groupBalances, setGroupBalances] = useState<WalletGroupBalance[]>([]);
  const [settlementSuggestions, setSettlementSuggestions] = useState<SettlementSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [partialWarning, setPartialWarning] = useState<string | null>(null);

  async function loadWalletData() {
    try {
      setLoading(true);
      setError(null);
      setPartialWarning(null);

      const [currentUserResult, groupsResult] = await Promise.allSettled([
        getCurrentUser(),
        getMyGroups(),
      ]);
      const currentUser = currentUserResult.status === 'fulfilled' ? currentUserResult.value : null;

      if (groupsResult.status === 'rejected') {
        throw groupsResult.reason;
      }

      const currentUserId = currentUser?.id ? String(currentUser.id) : null;
      const activeGroups = groupsResult.value.filter(isActiveGroup);
      const results = await Promise.allSettled(
        activeGroups.map(async (group): Promise<GroupWalletData> => {
          const [myBalanceResult, balancesResult, settlementsResult, expensesResult, planResult] =
            await Promise.allSettled([
              getMyGroupBalance(group.id),
              getGroupBalances(group.id),
              listGroupSettlements(group.id),
              listGroupExpenses(group.id, { page_size: 10 }),
              getSettlementPlan(group.id).catch(() => null),
            ]);

          return {
            group,
            myBalance: myBalanceResult.status === 'fulfilled'
              ? myBalanceResult.value.net_balance_minor || 0
              : 0,
            balances: balancesResult.status === 'fulfilled'
              ? balancesResult.value.balances || []
              : [],
            settlements: settledValue(settlementsResult, []),
            expenses: settledValue(expensesResult, []),
            planItems: settledValue(planResult, null)?.items || [],
          };
        }),
      );

      const successfulGroups = results
        .filter((result): result is PromiseFulfilledResult<GroupWalletData> => result.status === 'fulfilled')
        .map((result) => result.value);
      const failedCount = results.length - successfulGroups.length;

      if (failedCount > 0) {
        setPartialWarning('بخشی از داده‌های کیف پول دریافت نشد، اما داده‌های موجود نمایش داده شد.');
      }

      const nextGroupBalances = successfulGroups.map((item) => ({
        groupId: item.group.id,
        groupTitle: getGroupTitle(item.group),
        netMinor: item.myBalance,
      }));

      const creditMinor = nextGroupBalances.reduce(
        (sum, item) => sum + (item.netMinor > 0 ? item.netMinor : 0),
        0,
      );
      const debtMinor = nextGroupBalances.reduce(
        (sum, item) => sum + (item.netMinor < 0 ? Math.abs(item.netMinor) : 0),
        0,
      );

      const nextTransactions = successfulGroups
        .flatMap((item) => {
          const nameMap = getNameMap(item.balances);
          const settlementTransactions = item.settlements
            .map((settlement) => buildSettlementTransaction(settlement, item.group, currentUserId, nameMap))
            .filter((transaction): transaction is WalletTransaction => Boolean(transaction));
          const expenseTransactions = item.expenses
            .map((expense) => buildExpenseTransaction(expense, item.group, currentUserId))
            .filter((transaction): transaction is WalletTransaction => Boolean(transaction));

          return [...settlementTransactions, ...expenseTransactions];
        })
        .sort((a, b) => b.createdAt - a.createdAt)
        .slice(0, 8);

      const nextSuggestions = successfulGroups
        .flatMap((item) =>
          item.planItems
            .map((planItem) => buildSettlementSuggestion(planItem, item.group, currentUserId))
            .filter((suggestion): suggestion is SettlementSuggestion => Boolean(suggestion)),
        )
        .sort((a, b) => b.amountMinor - a.amountMinor)
        .slice(0, 5);

      const openSettlementMinor = nextSuggestions.reduce((sum, item) => sum + item.amountMinor, 0);

      setSummary({
        creditMinor,
        debtMinor,
        netMinor: creditMinor - debtMinor,
        openSettlementMinor,
        activeGroupCount: activeGroups.length,
        settlementCount: successfulGroups.reduce((sum, item) => sum + item.settlements.length, 0),
        expenseCount: successfulGroups.reduce((sum, item) => sum + item.expenses.length, 0),
      });
      setTransactions(nextTransactions);
      setGroupBalances(nextGroupBalances.sort((a, b) => Math.abs(b.netMinor) - Math.abs(a.netMinor)));
      setSettlementSuggestions(nextSuggestions);
    } catch (loadError) {
      console.error(loadError);
      setError('فعلاً اطلاعات کیف پول در دسترس نیست. دوباره تلاش کن.');
      setSummary(emptySummary);
      setTransactions([]);
      setGroupBalances([]);
      setSettlementSuggestions([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadWalletData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const netTone = summary.netMinor >= 0 ? 'positive' : 'negative';
  const netLabel = summary.netMinor >= 0 ? 'طلبکار هستید' : 'بدهکار هستید';
  const HeroDirectionIcon = summary.netMinor >= 0 ? ArrowDown : ArrowUp;
  const topGroups = useMemo(() => groupBalances.slice(0, 5), [groupBalances]);

  return (
    <main className="px-4 py-6 sm:px-6 xl:px-8">
      <div className="mx-auto grid max-w-[1240px] gap-6 xl:grid-cols-[minmax(0,1fr)_354px]">
        <section className="min-w-0 space-y-6">
          <div className="flex flex-col gap-4 text-right sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h1 className="text-[32px] font-extrabold leading-tight text-text">کیف پول</h1>
              <p className="mt-2 text-base text-muted">
                خلاصه حساب گروه‌ها، تسویه‌ها و رفت‌وآمدهای مالی تو در اینجا نمایش داده می‌شود.
              </p>
            </div>

            <button
              type="button"
              onClick={loadWalletData}
              disabled={loading}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl border border-border bg-white px-4 text-sm font-bold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <RefreshCw className={['h-4 w-4', loading ? 'animate-spin' : ''].join(' ')} />
              به‌روزرسانی
            </button>
          </div>

          {error ? (
            <div className="rounded-3xl border border-rose-100 bg-rose-50 p-5 text-center text-sm font-bold text-rose-600">
              {error}
            </div>
          ) : null}

          {partialWarning ? (
            <div className="rounded-3xl border border-amber-100 bg-amber-50 p-5 text-center text-sm font-bold text-amber-700">
              {partialWarning}
            </div>
          ) : null}

          <div className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-[#007A4F] via-[#009966] to-[#006B4D] p-7 text-white shadow-[0_24px_60px_rgba(0,128,89,0.22)]">
            <div className="pointer-events-none absolute -left-16 -top-16 h-52 w-52 rounded-full bg-white/10 blur-2xl" />
            <div className="pointer-events-none absolute bottom-3 right-8 text-[88px] opacity-15">
              <WalletCards />
            </div>

            <div className="relative grid gap-8 lg:grid-cols-[1.3fr_1fr_1fr_1fr] lg:items-center">
              <div className="text-right">
                <div className="mb-5 flex items-center justify-end gap-3 text-sm font-semibold text-white/85">
                  <WalletCards className="h-4.5 w-4.5" />
                  خالص حساب گروه‌ها
                </div>

                <div className="flex flex-wrap items-end justify-end gap-3">
                  {loading ? (
                    <span className="inline-flex items-center gap-2 text-2xl font-black">
                      <Loader2 className="h-6 w-6 animate-spin" />
                      در حال دریافت
                    </span>
                  ) : (
                    <>
                      <span className="text-[34px] font-black tracking-normal md:text-[44px]">
                        {formatMoney(Math.abs(summary.netMinor))}
                      </span>
                      <span className="mb-2 text-xl font-bold text-white/90">{netLabel}</span>
                    </>
                  )}
                </div>

                <button
                  type="button"
                  onClick={onOpenGroups}
                  className="mt-6 h-11 rounded-2xl border border-white/45 px-5 text-sm font-bold text-white transition hover:bg-white/12"
                >
                  مشاهده گروه‌ها
                </button>
              </div>

              <div className="border-white/20 lg:border-r lg:pr-8">
                <div className="text-sm text-white/75">در انتظار دریافت</div>
                <div className="mt-3 text-2xl font-black text-emerald-200">
                  +{formatMoney(summary.creditMinor)}
                </div>
              </div>

              <div className="border-white/20 lg:border-r lg:pr-8">
                <div className="text-sm text-white/75">در انتظار پرداخت</div>
                <div className="mt-3 text-2xl font-black text-orange-300">
                  -{formatMoney(summary.debtMinor)}
                </div>
              </div>

              <div className="border-white/20 lg:border-r lg:pr-8">
                <div className="text-sm text-white/75">تسویه‌های باز</div>
                <div className="mt-3 text-2xl font-black text-white">
                  {formatMoney(summary.openSettlementMinor)}
                </div>
              </div>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <ActionButton icon={Plus} label="ثبت هزینه" onClick={onOpenActivities} />
            <ActionButton icon={Users} label="گروه‌ها" onClick={onOpenGroups} />
            <ActionButton icon={CreditCard} label="تسویه حساب" onClick={onOpenGroups} />
            <ActionButton icon={RefreshCw} label="به‌روزرسانی" onClick={loadWalletData} loading={loading} />
          </div>

          <div className="overflow-hidden rounded-3xl border border-border bg-white shadow-soft">
            <div className="flex items-center justify-between border-b border-border px-6 py-5">
              <button
                type="button"
                onClick={onOpenActivities}
                className="text-sm font-bold text-emerald-600 transition hover:text-emerald-700"
              >
                مشاهده فعالیت‌ها
              </button>
              <h2 className="text-2xl font-extrabold text-text">تراکنش‌های اخیر</h2>
            </div>

            {loading ? (
              <EmptyState
                icon={Loader2}
                title="در حال دریافت تراکنش‌ها"
                description="در حال آماده‌کردن تراکنش‌های اخیر هستیم."
              />
            ) : null}

            {!loading && transactions.length === 0 ? (
              <EmptyState
                icon={History}
                title="تراکنشی برای نمایش نیست"
                description="بعد از ثبت هزینه یا تسویه حساب در گروه‌ها، ردیف‌های کیف پول اینجا نمایش داده می‌شوند."
              />
            ) : null}

            {!loading && transactions.length > 0 ? (
              <div>
                {transactions.map((transaction) => (
                  <TransactionRow key={transaction.id} transaction={transaction} />
                ))}
              </div>
            ) : null}
          </div>

          <div className="overflow-hidden rounded-3xl border border-border bg-white shadow-soft">
            <div className="flex items-center justify-between border-b border-border px-6 py-5">
              <button
                type="button"
                onClick={onOpenGroups}
                className="text-sm font-bold text-emerald-600 transition hover:text-emerald-700"
              >
                مشاهده گروه‌ها
              </button>
              <h2 className="text-2xl font-extrabold text-text">تسویه‌های پیشنهادی</h2>
            </div>

            <div className="px-5">
              {settlementSuggestions.map((item) => (
                <SettlementSuggestionRow key={item.id} item={item} />
              ))}
            </div>

            {!loading && settlementSuggestions.length === 0 ? (
              <EmptyState
                icon={CheckCircle2}
                title="تسویه بازی ندارید"
                description="اگر برای تسویه گروه‌ها پیشنهادی وجود داشته باشد، اینجا به تو نشان داده می‌شود."
              />
            ) : null}
          </div>
        </section>

        <aside className="space-y-6">
          <div className="rounded-3xl border border-border bg-white p-6 shadow-soft">
            <div className="mb-6 flex items-center justify-between">
              <div className={['flex h-12 w-12 items-center justify-center rounded-2xl', netTone === 'positive' ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-500'].join(' ')}>
                <HeroDirectionIcon className="h-5.5 w-5.5" />
              </div>
              <h2 className="text-xl font-extrabold text-text">خلاصه کیف پول</h2>
            </div>

            <div className="space-y-5">
              <SummaryRow label="خالص حساب گروه‌ها" value={formatSignedMoney(summary.netMinor)} tone={netTone} />
              <SummaryRow label="در انتظار دریافت" value={`+${formatMoney(summary.creditMinor)}`} tone="positive" />
              <SummaryRow label="در انتظار پرداخت" value={`-${formatMoney(summary.debtMinor)}`} tone="negative" />
              <SummaryRow label="تسویه‌های باز" value={formatMoney(summary.openSettlementMinor)} />
              <SummaryRow label="گروه‌های فعال" value={summary.activeGroupCount.toLocaleString('fa-IR')} />
              <SummaryRow label="تسویه‌های ثبت‌شده" value={summary.settlementCount.toLocaleString('fa-IR')} />
              <SummaryRow label="هزینه‌های ثبت‌شده" value={summary.expenseCount.toLocaleString('fa-IR')} />
            </div>
          </div>

          <div className="rounded-3xl border border-border bg-white p-6 shadow-soft">
            <div className="mb-4 flex items-center justify-between">
              <button
                type="button"
                onClick={onOpenGroups}
                className="text-sm font-bold text-emerald-600 transition hover:text-emerald-700"
              >
                همه
              </button>
              <h2 className="text-xl font-extrabold text-text">حساب گروه‌ها</h2>
            </div>

            {topGroups.length > 0 ? (
              <div>
                {topGroups.map((item) => (
                  <GroupBalanceRow key={item.groupId} item={item} />
                ))}
              </div>
            ) : (
              <div className="rounded-2xl border border-dashed border-border p-5 text-center text-sm leading-7 text-muted">
                هنوز بالانسی برای گروه‌های شما دریافت نشده است.
              </div>
            )}
          </div>

          <div className="rounded-3xl border border-border bg-white p-6 shadow-soft">
            <h2 className="mb-3 text-xl font-extrabold text-text">اقدامات سریع</h2>
            <QuickAction icon={ReceiptText} label="ثبت یا مشاهده هزینه‌ها" onClick={onOpenActivities} />
            <QuickAction icon={Users} label="مدیریت گروه‌ها" onClick={onOpenGroups} />
            <QuickAction icon={Send} label="مشاهده تسویه‌ها" onClick={onOpenGroups} />
            <QuickAction icon={RefreshCw} label="تازه‌سازی اطلاعات" onClick={loadWalletData} />
          </div>

          <div className="rounded-3xl border border-emerald-100 bg-emerald-50/60 p-6 shadow-soft">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white text-emerald-600 shadow-sm">
                <Clock3 className="h-5.5 w-5.5" />
              </div>
              <div className="text-right">
                <h2 className="text-lg font-extrabold text-text">وضعیت این صفحه</h2>
                <p className="mt-1 text-sm text-muted">خلاصه هزینه‌ها و تسویه‌ها</p>
              </div>
            </div>

            <div className="flex items-start gap-3 rounded-2xl bg-white/70 p-4 text-right text-sm leading-7 text-slate-600">
              <AlertCircle className="mt-1 h-5 w-5 shrink-0 text-emerald-600" />
              موجودی این صفحه از حساب گروه‌ها، تسویه‌ها و هزینه‌های ثبت‌شده ساخته می‌شود.
            </div>
          </div>
        </aside>
      </div>
    </main>
  );
}
