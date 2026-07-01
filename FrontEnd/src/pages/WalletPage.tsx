import { useEffect, useMemo, useState } from 'react';
import {
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  CheckCircle2,
  CreditCard,
  Eye,
  Grid3X3,
  History,
  Loader2,
  Plus,
  ReceiptText,
  RefreshCw,
  Scale,
  TrendingUp,
  Users,
  WalletCards,
  type LucideIcon,
} from 'lucide-react';
import { listGroupExpenses, type BackendExpense, type ExpenseParticipant } from '../lib/expenseApi';
import { getGroupBalances, getMyGroupBalance, getSettlementPlan, listGroupSettlements, type BalanceItem, type SettlementItem, type SettlementPlanItem } from '../lib/settlementApi';
import { getMyGroups, type BackendGroup } from '../lib/groupApi';
import { MoneyWithWords } from '../lib/money';
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
  groupTitle: string;
  kindLabel: string;
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
  const digits = Math.abs(Math.round(amount)).toLocaleString('fa-IR');
  return `تومان \u2066${digits}\u2069`;
}

function formatSignedMoney(amount: number) {
  const digits = Math.abs(Math.round(amount)).toLocaleString('fa-IR');
  const sign = amount > 0 ? '+' : amount < 0 ? '−' : '';
  return `تومان \u2066${sign}${digits}\u2069`;
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
    groupTitle: getGroupTitle(group),
    kindLabel: amount >= 0 ? 'طلب' : 'پرداخت',
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
    groupTitle: getGroupTitle(group),
    kindLabel: amount >= 0 ? 'پرداخت' : 'هزینه',
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
  tone = 'secondary',
}: {
  icon: LucideIcon;
  label: string;
  onClick?: () => void;
  loading?: boolean;
  tone?: 'primary' | 'secondary';
}) {
  const ButtonIcon = loading ? Loader2 : Icon;

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={loading}
      className={[
        'group flex h-12 items-center justify-center gap-2 rounded-[16px] border px-4 text-sm font-black transition disabled:cursor-not-allowed disabled:opacity-70',
        tone === 'primary'
          ? 'border-emerald-600 bg-emerald-600 text-white shadow-[0_14px_30px_rgba(5,150,105,0.18)] hover:bg-emerald-700 dark:border-emerald-500 dark:bg-emerald-500 dark:hover:bg-emerald-400'
          : 'border-emerald-300 bg-white text-emerald-700 hover:bg-emerald-50 dark:border-emerald-500/35 dark:bg-slate-950 dark:text-emerald-200 dark:hover:bg-emerald-500/10',
      ].join(' ')}
    >
      <span className={[
        'flex h-8 w-8 items-center justify-center rounded-[12px] transition',
        tone === 'primary' ? 'bg-white/14 text-white' : 'bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-200',
      ].join(' ')}>
        <ButtonIcon className={['h-4 w-4', loading ? 'animate-spin' : ''].join(' ')} />
      </span>
      {label}
    </button>
  );
}

function TransactionRow({ transaction }: { transaction: WalletTransaction }) {
  const isPositive = transaction.tone === 'positive';

  return (
    <div className="grid min-w-0 gap-3 border-b border-slate-100 px-4 py-3.5 last:border-b-0 md:grid-cols-[minmax(170px,1.35fr)_minmax(90px,0.6fr)_minmax(80px,0.5fr)_minmax(120px,0.75fr)_minmax(110px,0.7fr)] md:items-center dark:border-slate-800">
      <div className="min-w-0 overflow-hidden text-right">
        <p title={transaction.title} className="block max-w-full truncate text-sm font-black text-text dark:text-slate-100">{transaction.title}</p>
        <p title={transaction.subtitle} className="mt-1 block max-w-full truncate text-[11px] font-semibold text-muted dark:text-slate-400 md:hidden">{transaction.subtitle}</p>
      </div>

      <p title={transaction.groupTitle} className="min-w-0 truncate text-xs font-black text-slate-700 dark:text-slate-200"><span className="font-semibold text-muted md:hidden">گروه: </span>{transaction.groupTitle}</p>

      <div className="min-w-0">
        <span className={[
          'inline-flex max-w-full truncate rounded-full px-2.5 py-1 text-[10px] font-black',
          isPositive ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-200' : 'bg-rose-50 text-rose-600 dark:bg-rose-500/10 dark:text-rose-200',
        ].join(' ')}>
          {transaction.kindLabel}
        </span>
      </div>

      <p title={formatSignedMoney(transaction.amount)} className={['min-w-0 truncate text-sm font-black', isPositive ? 'text-emerald-600 dark:text-emerald-200' : 'text-rose-500 dark:text-rose-200'].join(' ')}><span className="font-semibold text-muted md:hidden">مبلغ: </span>{formatSignedMoney(transaction.amount)}</p>

      <div className="min-w-0 overflow-hidden text-xs font-semibold text-muted dark:text-slate-400">
        <p title={transaction.time} className="truncate">{transaction.time}</p>
        <p className="mt-1 truncate text-[10px]">{transaction.statusLabel}</p>
      </div>
    </div>
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
      <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-200">
        <Icon className="h-6 w-6" />
      </div>
      <h3 className="text-base font-extrabold text-text dark:text-slate-100">{title}</h3>
      <p className="mx-auto mt-2 max-w-[360px] text-sm leading-7 text-muted dark:text-slate-400">{description}</p>
    </div>
  );
}

function SettlementSuggestionRow({ item }: { item: SettlementSuggestion }) {
  const isPositive = item.tone === 'positive';

  return (
    <div className="flex min-w-0 items-center justify-between gap-4 border-b border-slate-100 py-3.5 last:border-b-0 dark:border-slate-800">
      <div className="text-left">
        <div className={['text-sm font-black', isPositive ? 'text-emerald-600 dark:text-emerald-200' : 'text-rose-500 dark:text-rose-200'].join(' ')}>
          {formatMoney(item.amountMinor)}
        </div>
        <div className="mt-1 text-xs text-muted dark:text-slate-400">{item.statusLabel}</div>
      </div>
      <div className="min-w-0 text-right">
        <div className="truncate text-sm font-bold text-text dark:text-slate-100">{item.personName}</div>
        <div className="mt-1 truncate text-xs text-muted dark:text-slate-400">
          {item.description} در «{item.groupTitle}»
        </div>
      </div>
    </div>
  );
}

function GroupBalanceRow({ item }: { item: WalletGroupBalance }) {
  const isPositive = item.netMinor >= 0;
  const isSettled = item.netMinor === 0;

  return (
    <div className="flex min-w-0 items-center gap-3 border-b border-slate-100 py-3 last:border-b-0 dark:border-slate-800">
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-xs font-black text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-200">{getAvatarText(item.groupTitle)}</span>
      <div className="min-w-0 flex-1 text-right">
        <div title={item.groupTitle} className="truncate text-sm font-black text-text dark:text-slate-100">{item.groupTitle}</div>
      </div>
      <span className={[
        'shrink-0 rounded-full px-2.5 py-1 text-[10px] font-black',
        isSettled ? 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-300' : isPositive ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-200' : 'bg-rose-50 text-rose-600 dark:bg-rose-500/10 dark:text-rose-200',
      ].join(' ')}>{isSettled ? 'تسویه‌شده' : isPositive ? 'طلبکارید' : 'بدهکارید'}</span>
      <div title={formatSignedMoney(item.netMinor)} className={['max-w-[120px] shrink-0 truncate text-left text-sm font-black', isSettled ? 'text-slate-500 dark:text-slate-300' : isPositive ? 'text-emerald-600 dark:text-emerald-200' : 'text-rose-500 dark:text-rose-200'].join(' ')}>
        {formatSignedMoney(item.netMinor)}
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

  const netLabel = summary.netMinor > 0 ? 'طلبکار هستید' : summary.netMinor < 0 ? 'بدهکار هستید' : 'حساب‌ها تسویه‌اند';
  const topGroups = useMemo(() => groupBalances.slice(0, 3), [groupBalances]);
  const bannerLabel = summary.netMinor > 0
    ? `${formatMoney(summary.netMinor)} طلب دارید`
    : summary.netMinor < 0
      ? `${formatMoney(summary.netMinor)} بدهی دارید`
      : 'همه حساب‌های شما تسویه است';
  const bannerSuggestion = summary.netMinor > 0
    ? 'طلب‌ها را بررسی کنید و در صورت نیاز یادآوری بفرستید.'
    : summary.netMinor < 0
      ? 'پرداخت‌های باز را بررسی و تسویه کنید.'
      : 'با ثبت هزینه جدید، وضعیت حساب‌ها اینجا به‌روز می‌شود.';

  return (
    <main dir="rtl" className="px-3 py-4 text-right sm:px-6 sm:py-6 xl:px-8">
      <div className="mx-auto max-w-[1180px] space-y-5">
        <section dir="ltr" className="grid items-center gap-4 rounded-[22px] border border-slate-200 bg-white/95 p-4 shadow-[0_14px_38px_rgba(15,23,42,0.055)] md:grid-cols-[auto_minmax(0,1fr)_auto] dark:border-slate-700 dark:bg-slate-950/90 dark:shadow-[0_18px_48px_rgba(0,0,0,0.22)]">
          <button
            type="button"
            onClick={onOpenGroups}
            className="order-3 inline-flex h-11 items-center justify-center gap-2 rounded-[14px] border border-emerald-500 bg-white px-4 text-sm font-black text-emerald-700 transition hover:bg-emerald-50 md:order-1 dark:bg-slate-950 dark:text-emerald-200 dark:hover:bg-emerald-500/10"
          >
            <Eye className="h-4 w-4" />
            {summary.netMinor > 0 ? 'مشاهده طلب‌ها' : 'مشاهده گروه‌ها'}
          </button>

          <div dir="rtl" className="order-2 min-w-0 text-center md:text-right">
            <p className="text-sm font-black leading-7 text-text dark:text-slate-100 sm:text-base">
              {summary.netMinor === 0 ? (
                <>حساب شما در {summary.activeGroupCount.toLocaleString('fa-IR')} گروه <span className="text-emerald-600 dark:text-emerald-300">کاملاً تسویه است</span></>
              ) : (
                <>شما در {summary.activeGroupCount.toLocaleString('fa-IR')} گروه، مجموعاً <span className="text-emerald-600 dark:text-emerald-300">{bannerLabel}</span></>
              )}
            </p>
            <p className="mt-1 text-xs font-semibold leading-6 text-muted dark:text-slate-400"><span className="font-black text-emerald-600 dark:text-emerald-300">پیشنهاد:</span> {bannerSuggestion}</p>
          </div>

          <button
            type="button"
            onClick={() => void loadWalletData()}
            disabled={loading}
            className="order-1 mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-50 text-emerald-600 transition hover:bg-emerald-100 disabled:opacity-60 md:order-3 dark:bg-emerald-500/10 dark:text-emerald-200 dark:hover:bg-emerald-500/15"
            aria-label="به‌روزرسانی کیف پول"
          >
            {loading ? <Loader2 className="h-6 w-6 animate-spin" /> : <TrendingUp className="h-6 w-6" />}
          </button>
        </section>

        {error ? <div className="rounded-[18px] border border-rose-200 bg-rose-50 p-4 text-center text-sm font-bold text-rose-600 dark:border-rose-500/25 dark:bg-rose-500/10 dark:text-rose-200">{error}</div> : null}
        {partialWarning ? <div className="rounded-[18px] border border-amber-200 bg-amber-50 p-4 text-center text-sm font-bold text-amber-700 dark:border-amber-500/25 dark:bg-amber-500/10 dark:text-amber-200">{partialWarning}</div> : null}

        <section dir="ltr" className="grid gap-5 xl:grid-cols-[360px_minmax(0,1fr)] xl:items-stretch">
          <aside dir="rtl" className="order-2 overflow-hidden rounded-[22px] border border-slate-200 bg-white shadow-[0_12px_34px_rgba(15,23,42,0.05)] xl:order-1 dark:border-slate-700 dark:bg-slate-950/90">
            <div className="flex items-center justify-between border-b border-slate-100 px-4 py-4 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <span className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-200"><Users className="h-4 w-4" /></span>
                <h2 className="text-base font-black text-text dark:text-slate-100">وضعیت گروه‌ها</h2>
              </div>
              <span className="text-xs font-bold text-muted dark:text-slate-400">{summary.activeGroupCount.toLocaleString('fa-IR')} گروه</span>
            </div>

            <div className="px-4">
              {topGroups.length > 0 ? topGroups.map((item) => <GroupBalanceRow key={item.groupId} item={item} />) : (
                <div className="py-8 text-center text-sm font-semibold leading-7 text-muted dark:text-slate-400">هنوز بالانسی برای گروه‌های شما وجود ندارد.</div>
              )}
            </div>

            <div className="border-t border-slate-100 p-3 dark:border-slate-800">
              <button type="button" onClick={onOpenGroups} className="flex h-11 w-full items-center justify-center gap-2 rounded-[14px] border border-slate-200 text-sm font-black text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-900">
                <Grid3X3 className="h-4 w-4" />
                مشاهده همه گروه‌ها
              </button>
            </div>
          </aside>

          <div dir="rtl" className="order-1 min-w-0 xl:order-2">
            <section className="relative overflow-hidden rounded-[24px] bg-gradient-to-br from-[#007A4F] via-[#009966] to-[#006B4D] p-5 text-white shadow-[0_20px_48px_rgba(0,128,89,0.22)] sm:p-6">
              <div className="pointer-events-none absolute -left-20 -top-20 h-64 w-64 rounded-full bg-white/10 blur-3xl" />
              <div className="relative">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-black text-white/85">خالص حساب شما</p>
                    <div className="mt-2">
                      {loading ? (
                        <span className="inline-flex items-center gap-2 text-2xl font-black"><Loader2 className="h-6 w-6 animate-spin" />در حال دریافت</span>
                      ) : (
                        <MoneyWithWords amount={Math.abs(summary.netMinor)} valueClassName="text-[34px] font-black tracking-[-0.04em] sm:text-[44px]" textClassName="mt-1 text-xs font-semibold text-white/70" showText={true} />
                      )}
                    </div>
                  </div>
                  <span className="inline-flex items-center gap-2 rounded-full bg-white/12 px-3 py-2 text-xs font-black text-white ring-1 ring-white/15"><CheckCircle2 className="h-4 w-4" />{netLabel}</span>
                </div>

                <div className="mt-5 grid gap-3 sm:grid-cols-2">
                  <div className="flex min-w-0 items-center justify-between gap-3 rounded-[18px] border border-white/20 bg-white/[0.06] p-4">
                    <div className="min-w-0"><p className="text-xs font-bold text-white/75">طلب شما</p><p title={formatMoney(summary.creditMinor)} className="mt-2 truncate text-lg font-black text-white">{formatMoney(summary.creditMinor)}</p><p className="mt-1 text-[10px] font-semibold text-white/65">از {groupBalances.filter((item) => item.netMinor > 0).length.toLocaleString('fa-IR')} گروه</p></div>
                    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white/10 text-emerald-100"><ArrowDown className="h-5 w-5" /></span>
                  </div>
                  <div className="flex min-w-0 items-center justify-between gap-3 rounded-[18px] border border-white/20 bg-white/[0.06] p-4">
                    <div className="min-w-0"><p className="text-xs font-bold text-white/75">بدهی شما</p><p title={formatMoney(summary.debtMinor)} className="mt-2 truncate text-lg font-black text-white">{formatMoney(summary.debtMinor)}</p><p className="mt-1 text-[10px] font-semibold text-white/65">در {groupBalances.filter((item) => item.netMinor < 0).length.toLocaleString('fa-IR')} گروه</p></div>
                    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white/10 text-orange-100"><ArrowUp className="h-5 w-5" /></span>
                  </div>
                </div>
              </div>
            </section>

            <div className="mt-4 grid grid-cols-2 gap-3">
              <ActionButton tone="primary" icon={Plus} label="ثبت هزینه" onClick={onOpenActivities} />
              <ActionButton tone="secondary" icon={CreditCard} label="تسویه حساب" onClick={onOpenGroups} />
            </div>
          </div>
        </section>

        <section dir="ltr" className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px] xl:items-stretch">
          <div dir="rtl" className="order-2 overflow-hidden rounded-[22px] border border-slate-200 bg-white shadow-[0_12px_34px_rgba(15,23,42,0.05)] xl:order-1 dark:border-slate-700 dark:bg-slate-950/90">
            <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-4 py-4 dark:border-slate-800 sm:px-5">
              <h2 className="text-lg font-black text-text dark:text-slate-100">تراکنش‌های اخیر</h2>
              <button type="button" onClick={onOpenActivities} className="inline-flex items-center gap-1 text-xs font-black text-emerald-600 hover:text-emerald-700 dark:text-emerald-300">مشاهده همه تراکنش‌ها<ArrowLeft className="h-4 w-4" /></button>
            </div>

            {transactions.length > 0 ? (
              <div className="hidden min-w-0 grid-cols-[minmax(170px,1.35fr)_minmax(90px,0.6fr)_minmax(80px,0.5fr)_minmax(120px,0.75fr)_minmax(110px,0.7fr)] gap-3 border-b border-slate-100 bg-slate-50/60 px-4 py-3 text-[11px] font-black text-slate-500 md:grid dark:border-slate-800 dark:bg-slate-900/60 dark:text-slate-400">
                <span>عنوان تراکنش</span><span>گروه</span><span>نوع</span><span>مبلغ</span><span>تاریخ</span>
              </div>
            ) : null}

            {loading ? <EmptyState icon={Loader2} title="در حال دریافت تراکنش‌ها" description="در حال آماده‌کردن تراکنش‌های اخیر هستیم." /> : null}
            {!loading && transactions.length === 0 ? <EmptyState icon={History} title="تراکنشی برای نمایش نیست" description="بعد از ثبت هزینه یا تسویه، تراکنش‌ها اینجا نمایش داده می‌شوند." /> : null}
            {!loading && transactions.length > 0 ? <div>{transactions.map((transaction) => <TransactionRow key={transaction.id} transaction={transaction} />)}</div> : null}
          </div>

          <aside dir="rtl" className="order-1 flex min-h-[390px] flex-col overflow-hidden rounded-[22px] border border-slate-200 bg-white shadow-[0_12px_34px_rgba(15,23,42,0.05)] xl:order-2 dark:border-slate-700 dark:bg-slate-950/90">
            <div className="flex items-center gap-2 border-b border-slate-100 px-4 py-4 dark:border-slate-800">
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-200"><Scale className="h-4 w-4" /></span>
              <h2 className="text-base font-black text-text dark:text-slate-100">پیشنهادهای تسویه حساب</h2>
            </div>

            {settlementSuggestions.length > 0 ? (
              <div className="flex-1 px-4">{settlementSuggestions.map((item) => <SettlementSuggestionRow key={item.id} item={item} />)}</div>
            ) : (
              <div className="flex flex-1 flex-col items-center justify-center px-6 py-7 text-center">
                <div className="relative flex h-28 w-28 items-center justify-center rounded-full bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-200">
                  <WalletCards className="h-12 w-12" />
                  <CheckCircle2 className="absolute -bottom-1 -right-1 h-10 w-10 rounded-full bg-white fill-emerald-600 text-white dark:bg-slate-950" />
                </div>
                <h3 className="mt-5 text-base font-black text-text dark:text-slate-100">همه حساب‌ها فعلاً تسویه‌اند</h3>
                <p className="mt-2 text-xs font-semibold leading-7 text-muted dark:text-slate-400">پس از ثبت هزینه یا پرداخت جدید، پیشنهادها اینجا نمایش داده می‌شوند.</p>
              </div>
            )}

            <div className="grid grid-cols-2 gap-2 border-t border-slate-100 p-3 dark:border-slate-800">
              <button type="button" onClick={onOpenActivities} className="flex h-10 items-center justify-center gap-1.5 rounded-[12px] bg-emerald-600 px-2 text-xs font-black text-white transition hover:bg-emerald-700 dark:bg-emerald-500 dark:hover:bg-emerald-400"><Plus className="h-4 w-4" />ثبت هزینه جدید</button>
              <button type="button" onClick={onOpenGroups} className="flex h-10 items-center justify-center gap-1.5 rounded-[12px] border border-emerald-400 px-2 text-xs font-black text-emerald-700 transition hover:bg-emerald-50 dark:border-emerald-500/35 dark:text-emerald-200 dark:hover:bg-emerald-500/10"><Eye className="h-4 w-4" />مشاهده طلب‌ها</button>
            </div>
          </aside>
        </section>
      </div>
    </main>
  );
}
