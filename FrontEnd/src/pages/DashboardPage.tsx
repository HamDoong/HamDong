import {
  AlertCircle,
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  Bell,
  CheckCircle2,
  CreditCard,
  Home,
  Loader2,
  MoreVertical,
  Mountain,
  Plus,
  ReceiptText,
  TrendingUp,
  UserPlus,
  Users,
  UtensilsCrossed,
  WalletCards,
  type LucideIcon,
} from 'lucide-react';
import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { isApiError } from '../lib/api';
import {
  formatMoneyNumber as formatMoneyLabel,
  MoneyWithWords,
  numberToPersianWords,
  toPersianNumber,
} from '../lib/money';
import { getFriendlyNotificationBody } from '../lib/userMessages';
import { listGroupExpenses, type BackendExpense } from '../lib/expenseApi';
import {
  getNotificationMessages,
  type BackendNotificationMessage,
} from '../lib/notificationApi';
import {
  confirmPlanItem,
  getSettlementPlan,
  rejectPlanItem,
  sendPlanItemReminder,
  type SettlementPlanItem,
} from '../lib/settlementApi';
import { getCurrentUser } from '../lib/userApi';
import type { Group } from '../types';
import type { GroupBalanceSummary } from './GroupsPage';

interface DashboardPageProps {
  groups: Group[];
  groupBalances?: GroupBalanceSummary[];
  balancesLoading?: boolean;
  groupsLoading?: boolean;
  groupsError?: string | null;
  onCreateGroup: () => void;
  onOpenGroups: () => void;
  onOpenGroup: (groupId: string) => void;
  onOpenActivities: () => void;
  onOpenWallet: () => void;
}

interface SettlementSuggestion {
  id: string;
  description: string;
  amount: number;
  tone: Group['tone'];
  groupId?: string;
  groupName: string;
  itemId?: string;
  status?: string;
  referenceDate?: string;
}

interface DashboardEvent {
  id: string;
  title: string;
  time: string;
  timeText: string;
  icon: LucideIcon;
  toneClassName: string;
  createdAt: number;
  groupId?: string;
}

interface ActionNotice {
  tone: 'success' | 'info' | 'error';
  message: string;
}

function formatMoney(amount: number) {
  return formatMoneyLabel(amount);
}


function toEnglishDigits(value: string) {
  return value
    .replace(/[۰-۹]/g, (digit) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(digit)))
    .replace(/[٠-٩]/g, (digit) => String('٠١٢٣٤٥٦٧٨٩'.indexOf(digit)));
}

function getMemberCountText(label: string) {
  const match = toEnglishDigits(label).match(/(\d+)\s*عضو/);

  if (!match) return '';

  return `${numberToPersianWords(Number(match[1]))} عضو`;
}

function getPersonName(...values: Array<string | null | undefined>) {
  return values.find((value) => value && value.trim())?.trim() || 'عضو گروه';
}

function isArchivedGroup(group: Group) {
  return group.status === 'ARCHIVED';
}

function getGroupId(group: Group) {
  return String(group.id);
}

function getGroupById(groups: Group[]) {
  return new Map(groups.map((group) => [getGroupId(group), group]));
}

function getDateTimestamp(value?: string | null) {
  if (!value) return 0;

  const timestamp = new Date(value).getTime();
  return Number.isNaN(timestamp) ? 0 : timestamp;
}

function formatRelativeTime(value?: string | null) {
  const timestamp = getDateTimestamp(value);

  if (!timestamp) return 'زمان نامشخص';

  const diffMs = timestamp - Date.now();
  const absDiff = Math.abs(diffMs);
  const formatter = new Intl.RelativeTimeFormat('fa-IR', { numeric: 'auto' });

  if (absDiff < 60 * 1000) {
    return formatter.format(Math.round(diffMs / 1000), 'second');
  }

  if (absDiff < 60 * 60 * 1000) {
    return formatter.format(Math.round(diffMs / (60 * 1000)), 'minute');
  }

  if (absDiff < 24 * 60 * 60 * 1000) {
    return formatter.format(Math.round(diffMs / (60 * 60 * 1000)), 'hour');
  }

  if (absDiff < 7 * 24 * 60 * 60 * 1000) {
    return formatter.format(Math.round(diffMs / (24 * 60 * 60 * 1000)), 'day');
  }

  if (absDiff < 30 * 24 * 60 * 60 * 1000) {
    return formatter.format(Math.round(diffMs / (7 * 24 * 60 * 60 * 1000)), 'week');
  }

  if (absDiff < 365 * 24 * 60 * 60 * 1000) {
    return formatter.format(Math.round(diffMs / (30 * 24 * 60 * 60 * 1000)), 'month');
  }

  return formatter.format(Math.round(diffMs / (365 * 24 * 60 * 60 * 1000)), 'year');
}

function formatEventDate(value?: string | null) {
  const timestamp = getDateTimestamp(value);

  if (!timestamp) return 'بدون زمان';

  return new Intl.DateTimeFormat('fa-IR', {
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(timestamp));
}

function formatTaskAge(value?: string | null) {
  const timestamp = getDateTimestamp(value);
  if (!timestamp) return null;

  const days = Math.max(0, Math.floor((Date.now() - timestamp) / (24 * 60 * 60 * 1000)));
  return days === 0 ? 'کمتر از یک روز بدون تغییر' : `${days.toLocaleString('fa-IR')} روز بدون تغییر`;
}

function getExpenseTotal(expense: BackendExpense) {
  return (
    expense.total_amount_minor ??
    (expense.base_amount_minor || 0) +
      (expense.tax_amount_minor || 0) +
      (expense.service_fee_amount_minor || 0)
  );
}

function getNotificationBody(item: BackendNotificationMessage) {
  const metadata = typeof item.metadata === 'object' && item.metadata ? item.metadata : undefined;
  const data = typeof item.data === 'object' && item.data ? item.data : undefined;
  const metadataMessage =
    typeof metadata?.message === 'string'
      ? metadata.message
      : typeof data?.message === 'string'
        ? data.message
        : '';

  return getFriendlyNotificationBody({
    ...item,
    metadata: metadataMessage || item.metadata,
  });
}

function getNotificationIcon(item: BackendNotificationMessage): LucideIcon {
  const status = (item.status || '').toUpperCase();
  const type = (item.notification_type || item.message_type || '').toUpperCase();

  if (status === 'FAILED') return AlertCircle;
  if (type === 'SETTLEMENT' || type === 'REMINDER') return CreditCard;
  if (type === 'INVITE') return UserPlus;
  if (status === 'SENT' || status === 'DELIVERED') return CheckCircle2;

  return Bell;
}

function getNotificationToneClassName(item: BackendNotificationMessage) {
  const status = (item.status || '').toUpperCase();
  const priority = (item.priority || '').toUpperCase();

  if (status === 'FAILED' || priority === 'URGENT') return 'bg-rose-50 text-rose-500';
  if (status === 'PENDING' || status === 'SENDING' || priority === 'HIGH') return 'bg-amber-50 text-amber-500';
  if (status === 'SENT' || status === 'DELIVERED') return 'bg-emerald-50 text-emerald-600';

  return 'bg-slate-50 text-slate-600';
}

function notificationToEvent(item: BackendNotificationMessage): DashboardEvent {
  const date = item.created_at || item.sent_at || item.last_attempt_at || item.read_at;

  return {
    id: `notification-${item.id}`,
    title: getNotificationBody(item),
    time: formatRelativeTime(date),
    timeText: formatEventDate(date),
    icon: getNotificationIcon(item),
    toneClassName: getNotificationToneClassName(item),
    createdAt: getDateTimestamp(date),
  };
}

function expenseToEvent(
  expense: BackendExpense,
  group: Group,
  currentUserId: string | null,
): DashboardEvent {
  const date = expense.expense_date || expense.created_at || expense.updated_at;
  const total = getExpenseTotal(expense);
  const isMine = currentUserId && expense.payer_user_id === currentUserId;
  const title = isMine
    ? `شما هزینه «${expense.title}» را در «${group.name}» ثبت کردید`
    : `هزینه «${expense.title}» در «${group.name}» ثبت شد`;

  return {
    id: `expense-${expense.id}`,
    title: total > 0 ? `${title} - ${formatMoney(total)}` : title,
    time: formatRelativeTime(date),
    timeText: formatEventDate(date),
    icon: WalletCards,
    toneClassName: 'bg-emerald-50 text-emerald-600',
    createdAt: getDateTimestamp(date),
    groupId: getGroupId(group),
  };
}

function isOpenPlanItem(item: SettlementPlanItem) {
  const status = (item.status || '').toUpperCase();
  return status !== 'CONFIRMED' && status !== 'CANCELLED' && status !== 'COMPLETED';
}

function planItemToSuggestion(
  item: SettlementPlanItem,
  group: Group,
  currentUserId: string | null,
  referenceDate?: string,
): SettlementSuggestion | null {
  if (!isOpenPlanItem(item)) return null;

  const payerName = getPersonName(item.payer_display_name, item.payer_art_name);
  const receiverName = getPersonName(item.receiver_display_name, item.receiver_art_name);
  const isPayer = currentUserId ? item.payer_user_id === currentUserId : false;
  const isReceiver = currentUserId ? item.receiver_user_id === currentUserId : false;

  if (currentUserId && !isPayer && !isReceiver) return null;

  const description = isPayer
    ? `دریافت از ${receiverName} در گروه «${group.name}»`
    : isReceiver
      ? `پرداخت به ${payerName} در گروه «${group.name}»`
      : `تسویه پیشنهادی گروه «${group.name}»`;

  return {
    id: `plan-${item.id}`,
    description,
    amount: item.amount_minor,
    tone: isPayer ? 'negative' : 'positive',
    groupId: getGroupId(group),
    groupName: group.name,
    itemId: item.id,
    status: item.status,
    referenceDate,
  };
}

function balanceToSuggestion(
  balance: GroupBalanceSummary,
  group?: Group,
): SettlementSuggestion | null {
  if (balance.status === 'ARCHIVED' || balance.netMinor === 0) return null;

  const name = group?.name || balance.groupName;
  const isDebt = balance.netMinor < 0;

  return {
    id: `balance-${balance.groupId}`,
    description: isDebt
      ? 'برای تسویه این گروه پرداخت لازم دارید'
      : 'در این گروه طلبکار هستید',
    amount: Math.abs(balance.netMinor),
    tone: isDebt ? 'negative' : 'positive',
    groupId: balance.groupId,
    groupName: name,
  };
}

function mergeSuggestions(
  planSuggestions: SettlementSuggestion[],
  balanceSuggestions: SettlementSuggestion[],
) {
  const seen = new Set(planSuggestions.map((item) => item.groupId).filter(Boolean));

  return [...planSuggestions, ...balanceSuggestions.filter((item) => !seen.has(item.groupId))]
    .sort((a, b) => b.amount - a.amount)
    .slice(0, 3);
}

function SectionCard({
  children,
  className = '',
  variant = 'default',
}: {
  children: ReactNode;
  className?: string;
  variant?: 'default' | 'quiet';
}) {
  const variantClassName =
    variant === 'quiet'
      ? 'rounded-[24px] border border-slate-200/80 bg-white/[0.92] shadow-[0_16px_42px_rgba(15,23,42,0.085)] ring-1 ring-white/80 backdrop-blur'
      : 'rounded-[24px] border border-slate-200/85 bg-white/95 shadow-[0_20px_50px_rgba(15,23,42,0.095)] ring-1 ring-white/80 backdrop-blur';

  return (
    <section className={`dashboard-section-card dashboard-section-card--${variant} min-w-0 ${variantClassName} ${className}`}>
      {children}
    </section>
  );
}

function SectionHeader({
  title,
  actionLabel,
  icon,
  onAction,
  compact = false,
}: {
  title: string;
  actionLabel: string;
  icon: ReactNode;
  onAction?: () => void;
  compact?: boolean;
}) {
  return (
    <div className={[
      'dashboard-section-header',
      compact
        ? 'flex items-center justify-between gap-3 border-b border-emerald-50/80 bg-white/[0.35] px-4 py-3.5 sm:px-5'
        : 'mb-5 flex flex-wrap items-center justify-between gap-3',
    ].join(' ')}>
      <div className="flex items-center gap-2 text-right">
        {icon}
        <h2 className={compact ? 'text-base font-black text-text sm:text-lg' : 'text-lg font-black text-text sm:text-xl'}>{title}</h2>
      </div>

      <button
        type="button"
        onClick={onAction}
        className="dashboard-section-action inline-flex min-h-9 shrink-0 items-center gap-2 rounded-full px-3 text-xs font-extrabold text-emerald-600 transition hover:bg-emerald-50/60 hover:text-emerald-700"
      >
        {actionLabel}
        <ArrowLeft className="h-4 w-4" />
      </button>
    </div>
  );
}

function DashboardSectionState({
  icon: Icon,
  title,
  loading = false,
}: {
  icon: LucideIcon;
  title: string;
  description?: string;
  loading?: boolean;
}) {
  const StateIcon = loading ? Loader2 : Icon;

  return (
    <div className="dashboard-empty-state min-h-[140px] rounded-[20px] border border-dashed border-slate-200/90 bg-white/[0.82] px-4 py-6 text-center shadow-[0_10px_24px_rgba(15,23,42,0.055)]">
      <div className="dashboard-empty-state-icon mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-[16px] bg-white text-slate-500 shadow-sm">
        <StateIcon className={['h-5 w-5', loading ? 'animate-spin' : ''].join(' ')} />
      </div>
      <div className="text-sm font-black text-slate-700">{title}</div>
    </div>
  );
}

type QuickActionTone = 'emerald' | 'sky' | 'amber';

const quickActionToneClasses: Record<QuickActionTone, {
  button: string;
  icon: string;
  title: string;
}> = {
  emerald: {
    button: 'border-emerald-200/80 bg-gradient-to-l from-white via-emerald-50/95 to-emerald-50/85 shadow-[inset_3px_0_0_#10B981,0_0_0_1px_rgba(16,185,129,0.10),0_12px_30px_rgba(15,23,42,0.075)] hover:border-emerald-300 hover:shadow-[inset_3px_0_0_#10B981,0_0_0_1px_rgba(16,185,129,0.16),0_18px_38px_rgba(15,23,42,0.10)]',
    icon: 'text-emerald-600 group-hover:text-emerald-700',
    title: 'text-emerald-800',
  },
  sky: {
    button: 'border-sky-200/80 bg-gradient-to-l from-white via-sky-50/95 to-sky-50/85 shadow-[inset_3px_0_0_#0EA5E9,0_0_0_1px_rgba(14,165,233,0.10),0_12px_30px_rgba(15,23,42,0.075)] hover:border-sky-300 hover:shadow-[inset_3px_0_0_#0EA5E9,0_0_0_1px_rgba(14,165,233,0.16),0_18px_38px_rgba(15,23,42,0.10)]',
    icon: 'text-sky-600 group-hover:text-sky-700',
    title: 'text-sky-700',
  },
  amber: {
    button: 'border-orange-200/80 bg-gradient-to-l from-white via-orange-50/95 to-orange-50/85 shadow-[inset_3px_0_0_#F97316,0_0_0_1px_rgba(249,115,22,0.10),0_12px_30px_rgba(15,23,42,0.075)] hover:border-orange-300 hover:shadow-[inset_3px_0_0_#F97316,0_0_0_1px_rgba(249,115,22,0.16),0_18px_38px_rgba(15,23,42,0.10)]',
    icon: 'text-orange-600 group-hover:text-orange-700',
    title: 'text-orange-700',
  },
};

function QuickActionCard({
  icon: Icon,
  title,
  onClick,
  tone = 'emerald',
}: {
  icon: LucideIcon;
  title: string;
  onClick: () => void;
  tone?: QuickActionTone;
}) {
  const toneClasses = quickActionToneClasses[tone];

  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        `dashboard-quick-action dashboard-quick-action--${tone} group flex min-h-[82px] items-center justify-start gap-4 rounded-[22px] border px-5 text-right transition hover:-translate-y-0.5 xl:min-h-0 xl:flex-1`,
        toneClasses.button,
      ].join(' ')}
    >
      <div className={['dashboard-quick-action-icon flex h-11 w-11 shrink-0 items-center justify-center rounded-[16px] transition group-hover:scale-105', toneClasses.icon].join(' ')}>
        <Icon className="h-6 w-6" />
      </div>
      <div className="min-w-0 flex-1 text-right">
        <div className={['flex w-full items-center justify-start gap-2 text-right text-base font-black sm:text-lg', toneClasses.title].join(' ')}>
          <span className="w-full text-right">{title}</span>
        </div>
      </div>
    </button>
  );
}

function BalanceHero({
  creditMinor,
  debtMinor,
  loading,
  activeGroupCount,
  onOpenWallet,
}: {
  creditMinor: number;
  debtMinor: number;
  loading?: boolean;
  activeGroupCount: number;
  onOpenWallet: () => void;
}) {
  const netMinor = creditMinor - debtMinor;
  const isPositive = netMinor >= 0;
  const isBalanced = netMinor === 0;
  const statusLabel = isBalanced
    ? 'حساب شما تسویه است'
    : isPositive
      ? 'طلبکار هستید'
      : 'بدهکار هستید';
  const StatusIcon = isBalanced ? CheckCircle2 : isPositive ? TrendingUp : ArrowDown;

  return (
    <section className="dashboard-balance-card rounded-[28px] border border-emerald-100/80 bg-white/95 p-4 text-text shadow-[0_22px_58px_rgba(15,23,42,0.10)] backdrop-blur sm:p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3 text-right">
          <span className="dashboard-wallet-icon flex h-12 w-12 shrink-0 items-center justify-center rounded-[18px] bg-emerald-50 text-emerald-600 shadow-[inset_3px_0_0_#10B981]">
            <WalletCards className="h-6 w-6" strokeWidth={1.9} />
          </span>
          <div>
            <h1 className="text-lg font-black text-text sm:text-xl">وضعیت مالی شما</h1>
          </div>
        </div>

        <button
          type="button"
          onClick={onOpenWallet}
          className="dashboard-wallet-link inline-flex h-10 items-center justify-center gap-2 rounded-2xl border border-emerald-100 bg-emerald-50/70 px-4 text-xs font-black text-emerald-700 transition hover:-translate-y-0.5 hover:border-emerald-200 hover:bg-emerald-50"
        >
          جزئیات محاسبه
          <ArrowLeft className="h-4 w-4" />
        </button>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_300px]">
        <div className="dashboard-balance-main rounded-[24px] bg-gradient-to-br from-[#007A4F] via-[#009A66] to-[#0F766E] p-5 text-white shadow-[0_18px_42px_rgba(0,128,89,0.20)]">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="dashboard-balance-badge inline-flex min-h-9 items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 text-xs font-extrabold text-white/85">
              <Users className="h-4 w-4" />
              {activeGroupCount.toLocaleString('fa-IR')} گروه فعال
            </div>
            {!loading ? (
              <span className="dashboard-balance-status inline-flex items-center gap-2 rounded-full bg-white/12 px-3 py-2 text-xs font-black text-white">
                <StatusIcon className="h-4 w-4" />
                {statusLabel}
              </span>
            ) : null}
          </div>

          <div className="mt-7 text-right">
            <div className="text-xs font-extrabold text-white/68">
              {isBalanced ? 'همه چیز تسویه است' : 'در مجموع'}
            </div>
            <div className="mt-2 max-w-full break-words text-[32px] font-black tracking-normal sm:text-[44px]">
              {loading ? 'در حال محاسبه' : <MoneyWithWords amount={Math.abs(netMinor)} valueClassName="text-[32px] font-black tracking-normal sm:text-[44px]" textClassName="mt-2 text-sm font-semibold leading-7 text-white/68" showText={true} />}
            </div>
          </div>
        </div>

        <div className="grid gap-3">
          <div className="dashboard-balance-mini dashboard-balance-mini--credit flex min-h-[92px] items-center justify-between gap-4 rounded-[22px] border border-emerald-200/80 bg-gradient-to-l from-white via-emerald-50/70 to-emerald-50/60 px-4 py-3 shadow-[inset_3px_0_0_#10B981,0_0_0_1px_rgba(16,185,129,0.10),0_10px_24px_rgba(15,23,42,0.06)]">
            <span className="dashboard-balance-mini-icon flex h-11 w-11 shrink-0 items-center justify-center rounded-[16px] bg-emerald-600 text-white shadow-[0_10px_22px_rgba(16,185,129,0.22)] ring-1 ring-emerald-500/20">
              <ArrowDown className="h-5 w-5" strokeWidth={2.4} />
            </span>
            <div className="min-w-0 text-right">
              <div className="text-xs font-extrabold text-emerald-700/80">کل طلب‌ها</div>
              <div className="mt-1 text-xl font-black text-emerald-700"><MoneyWithWords amount={creditMinor} valueClassName="text-xl font-black text-emerald-700" textClassName="mt-1 text-[11px] font-semibold text-emerald-700/70" showText={true} /></div>
            </div>
          </div>

          <div className="dashboard-balance-mini dashboard-balance-mini--debt flex min-h-[92px] items-center justify-between gap-4 rounded-[22px] border border-orange-200/80 bg-gradient-to-l from-white via-orange-50/70 to-orange-50/60 px-4 py-3 text-right shadow-[inset_3px_0_0_#F97316,0_0_0_1px_rgba(249,115,22,0.10),0_10px_24px_rgba(15,23,42,0.06)]">
            <span className="dashboard-balance-mini-icon flex h-11 w-11 shrink-0 items-center justify-center rounded-[16px] bg-orange-500 text-white shadow-[0_10px_22px_rgba(249,115,22,0.22)] ring-1 ring-orange-500/20">
              <ArrowUp className="h-5 w-5" strokeWidth={2.4} />
            </span>
            <div className="min-w-0 flex-1 text-right">
              <div className="text-xs font-extrabold text-orange-700/80">کل بدهی‌ها</div>
              <div className="mt-1 text-xl font-black text-orange-700"><MoneyWithWords amount={debtMinor} valueClassName="text-xl font-black text-orange-700" textClassName="mt-1 text-[11px] font-semibold text-orange-700/70" showText={true} /></div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function SettlementRow({
  item,
  busy,
  onPrimary,
  onReminder,
  onReject,
  onDispute,
}: {
  item: SettlementSuggestion;
  busy: boolean;
  onPrimary: () => void;
  onReminder: () => void;
  onReject: () => void;
  onDispute: () => void;
}) {
  const [moreOpen, setMoreOpen] = useState(false);
  const isDebt = item.tone === 'negative';
  const canConfirmReceipt = !isDebt && Boolean(item.itemId) && String(item.status || '').toUpperCase() === 'REPORTED';
  const amountClassName = isDebt ? 'text-orange-700' : 'text-emerald-700';
  const iconClassName = isDebt
    ? 'bg-orange-50 text-orange-600 ring-orange-100'
    : 'bg-emerald-50 text-emerald-600 ring-emerald-100';
  const ActionIcon = isDebt ? ArrowUp : ArrowDown;
  const title = isDebt
    ? `در گروه «${item.groupName}» باید پول بگیرید`
    : `در گروه «${item.groupName}» باید پول بدهید`;
  const primaryLabel = isDebt ? 'تسویه' : canConfirmReceipt ? 'پول را گرفتم' : 'مشاهده وضعیت';
  const ageTimestamp = getDateTimestamp(item.referenceDate);
  const ageInDays = ageTimestamp ? Math.floor((Date.now() - ageTimestamp) / (24 * 60 * 60 * 1000)) : 0;
  const needsFollowUp = Boolean(ageTimestamp && ageInDays >= 7);
  const taskAgeLabel = formatTaskAge(item.referenceDate);

  return (
    <div className="dashboard-list-row dashboard-list-card dashboard-action-card w-full max-w-full min-w-0 rounded-[18px] border border-slate-200/85 bg-white/[0.92] p-3 text-right shadow-[0_8px_22px_rgba(15,23,42,0.055)] ring-1 ring-slate-100/70 sm:px-4 sm:py-3.5">
      <div className="flex min-w-0 items-start gap-2.5">
        <div className={`dashboard-event-icon flex h-9 w-9 shrink-0 items-center justify-center rounded-full ring-1 ${iconClassName}`}>
          <ActionIcon className="h-[18px] w-[18px]" strokeWidth={2.3} />
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex min-w-0 items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="truncate text-sm font-black leading-5 text-slate-700">{title}</div>
              <div className="mt-0.5 line-clamp-1 text-[11px] font-semibold leading-5 text-slate-500">{item.description}</div>
            </div>
            <MoneyWithWords amount={item.amount} valueClassName={`whitespace-nowrap text-sm font-black ${amountClassName}`} showText={false} />
          </div>

          <div className="mt-1.5 flex min-w-0 items-center gap-1.5 text-[10px] font-bold text-slate-400">
            <span>تسویه‌نشده</span>
            {taskAgeLabel ? <><span aria-hidden="true">•</span><span className="truncate">{taskAgeLabel}</span></> : null}
            {needsFollowUp ? <span className="shrink-0 rounded-full bg-amber-50 px-2 py-0.5 text-amber-700">نیازمند پیگیری</span> : null}
          </div>
        </div>
      </div>

      <div className="mt-2.5 flex items-center gap-1.5 border-t border-slate-100 pt-2.5">
        <button type="button" onClick={onPrimary} disabled={busy} className={`inline-flex h-9 min-w-[86px] items-center justify-center rounded-[12px] px-3 text-[11px] font-black text-white transition disabled:cursor-wait disabled:opacity-60 ${isDebt ? 'bg-orange-500 hover:bg-orange-600' : 'bg-emerald-600 hover:bg-emerald-700'}`}>
          {busy ? <Loader2 className="ml-1.5 h-4 w-4 animate-spin" /> : null}{primaryLabel}
        </button>
        <div className="relative mr-auto">
          <button type="button" onClick={() => setMoreOpen((current) => !current)} className="flex h-9 w-9 items-center justify-center rounded-full text-slate-500 transition hover:bg-slate-100" aria-label="اقدام‌های بیشتر" aria-expanded={moreOpen}>
            <MoreVertical className="h-[18px] w-[18px]" />
          </button>
          {moreOpen ? <div className="absolute bottom-10 left-0 z-20 w-36 overflow-hidden rounded-[14px] border border-slate-200 bg-white p-1.5 shadow-[0_14px_34px_rgba(15,23,42,0.16)]">
            {!isDebt && canConfirmReceipt ? <button type="button" onClick={() => { setMoreOpen(false); onReject(); }} disabled={busy} className="flex h-9 w-full items-center rounded-[9px] px-2.5 text-[11px] font-bold text-rose-600 hover:bg-rose-50 disabled:opacity-60">دریافت نکردم</button> : null}
            {!isDebt && !canConfirmReceipt ? <button type="button" onClick={() => { setMoreOpen(false); onReminder(); }} disabled={busy} className="flex h-9 w-full items-center rounded-[9px] px-2.5 text-[11px] font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-60">ارسال یادآوری</button> : null}
            <button type="button" onClick={() => { setMoreOpen(false); onDispute(); }} className="flex h-9 w-full items-center rounded-[9px] px-2.5 text-[11px] font-bold text-rose-600 hover:bg-rose-50">این مبلغ اشتباه است</button>
          </div> : null}
        </div>
      </div>
    </div>
  );
}

function EventRow({
  event,
  menuOpen,
  onToggleMenu,
  onView,
  onReport,
}: {
  event: DashboardEvent;
  menuOpen: boolean;
  onToggleMenu: () => void;
  onView: () => void;
  onReport: () => void;
}) {
  const Icon = event.icon;

  return (
    <div className="dashboard-list-row dashboard-list-card relative flex w-full max-w-full min-w-0 items-center gap-3 rounded-[20px] border border-slate-200/85 bg-white/[0.92] px-3 py-3 text-right shadow-[0_10px_26px_rgba(15,23,42,0.055)] ring-1 ring-slate-100/70 sm:px-4">
      <div className={`dashboard-event-icon flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${event.toneClassName}`}>
        <Icon className="h-5 w-5" />
      </div>

      <div className="min-w-0 flex-1">
        <p className="line-clamp-2 text-sm font-semibold leading-6 text-slate-600">{event.title}</p>
        <div className="mt-1 text-[11px] font-semibold text-slate-400">{event.time} · {event.timeText}</div>
      </div>

      <div className="relative shrink-0">
        <button type="button" onClick={onToggleMenu} className="flex h-10 w-10 items-center justify-center rounded-full text-slate-500 transition hover:bg-slate-100" aria-label={`اقدام‌های رویداد: ${event.title}`} title="اقدام‌های رویداد" aria-expanded={menuOpen}>
          <MoreVertical className="h-5 w-5" />
        </button>

        {menuOpen ? <div className="absolute left-0 top-11 z-20 w-40 overflow-hidden rounded-[15px] border border-slate-200 bg-white p-1.5 shadow-[0_14px_34px_rgba(15,23,42,0.16)]">
          <button type="button" onClick={onView} className="flex h-10 w-full items-center rounded-[10px] px-3 text-xs font-bold text-slate-700 hover:bg-slate-50">مشاهده</button>
          <button type="button" onClick={onReport} className="flex h-10 w-full items-center rounded-[10px] px-3 text-xs font-bold text-rose-600 hover:bg-rose-50">گزارش خطا</button>
        </div> : null}
      </div>
    </div>
  );
}

function GroupArtwork({ type }: { type: Group['illustration'] }) {
  const Icon = type === 'trip' ? Mountain : type === 'home' ? Home : UtensilsCrossed;
  const background =
    type === 'trip'
      ? 'from-sky-100 via-emerald-50 to-lime-100 text-emerald-700'
      : type === 'home'
        ? 'from-amber-100 via-orange-50 to-emerald-100 text-orange-700'
        : 'from-orange-100 via-amber-50 to-rose-100 text-orange-700';

  return (
    <div className={`dashboard-group-artwork dashboard-group-artwork--${type} relative flex h-[72px] w-[72px] shrink-0 items-center justify-center overflow-hidden rounded-full bg-gradient-to-br sm:h-20 sm:w-20 ${background}`}>
      <div className="absolute inset-x-0 bottom-0 h-6 bg-white/35" />
      <Icon className="relative h-9 w-9" strokeWidth={1.8} />
    </div>
  );
}

function DashboardGroupCard({
  id,
  title,
  membersLabel,
  statusLabel,
  amount,
  tone,
  illustration,
  onOpen,
}: {
  id: string;
  title: string;
  membersLabel: string;
  statusLabel: string;
  amount: number;
  tone: Group['tone'];
  illustration: Group['illustration'];
  onOpen: (groupId: string) => void;
}) {
  const isDebt = tone === 'negative';
  const isSettled = amount === 0;
  const toneClassName = isSettled
    ? 'dashboard-status-pill--neutral border-slate-200 bg-slate-50/90 text-slate-600'
    : isDebt
      ? 'dashboard-status-pill--negative border-orange-200 bg-orange-50/90 text-orange-700'
      : 'dashboard-status-pill--positive border-emerald-200 bg-emerald-50/90 text-emerald-700';
  const amountClassName = isSettled ? 'text-slate-600' : isDebt ? 'text-orange-700' : 'text-emerald-700';
  const amountTextClassName = isSettled ? 'text-slate-500' : isDebt ? 'text-orange-700/70' : 'text-emerald-700/70';

  return (
    <button
      type="button"
      onClick={() => onOpen(id)}
      className="dashboard-group-card group flex min-h-[178px] w-full min-w-0 flex-col justify-between overflow-hidden rounded-[26px] border border-slate-200/85 bg-gradient-to-br from-white via-white to-emerald-50/45 p-4 text-right shadow-[0_14px_34px_rgba(15,23,42,0.075)] ring-1 ring-slate-100/70 transition hover:-translate-y-0.5 hover:border-emerald-200 hover:bg-white hover:shadow-[0_18px_42px_rgba(15,23,42,0.105)] sm:p-5"
    >
      <div className="flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-lg font-black text-text">{title}</h3>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span className="dashboard-group-members inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white/80 px-2.5 py-1 text-[11px] font-extrabold text-slate-500">
              <Users className="h-3.5 w-3.5" />
              {membersLabel}
            </span>
            <span className={`inline-flex rounded-full border px-2.5 py-1 text-[11px] font-extrabold ${toneClassName}`}>
              {statusLabel}
            </span>
          </div>
        </div>
        <GroupArtwork type={illustration} />
      </div>

      <div className={`dashboard-group-amount dashboard-group-amount--${isSettled ? 'neutral' : isDebt ? 'debt' : 'credit'} mt-5 rounded-[20px] border border-white/70 bg-white/72 px-3.5 py-3 shadow-[inset_3px_0_0_rgba(16,185,129,0.22)]`}>
        <div className="mb-1 text-[11px] font-extrabold text-slate-400">
          {isSettled ? 'مانده گروه' : isDebt ? 'مبلغ قابل پرداخت' : 'مبلغ قابل دریافت'}
        </div>
        <MoneyWithWords
          amount={Math.abs(amount)}
          valueClassName={`text-xl font-black tracking-normal ${amountClassName}`}
          textClassName={`mt-1 hidden text-xs font-semibold leading-5 sm:block ${amountTextClassName}`}
        />
      </div>
    </button>
  );
}

function getDashboardTotals(groupBalances: GroupBalanceSummary[] = []) {
  const activeBalances = groupBalances.filter((item) => item.status !== 'ARCHIVED');

  if (activeBalances.length === 0) {
    return {
      creditMinor: 0,
      debtMinor: 0,
    };
  }

  return activeBalances.reduce(
    (totals, item) => {
      if (item.netMinor > 0) {
        totals.creditMinor += item.netMinor;
      }

      if (item.netMinor < 0) {
        totals.debtMinor += Math.abs(item.netMinor);
      }

      return totals;
    },
    { creditMinor: 0, debtMinor: 0 },
  );
}

function getGroupCards(groups: Group[], groupBalances: GroupBalanceSummary[] = []) {
  const balanceMap = new Map(groupBalances.map((item) => [String(item.groupId), item]));
  const activeGroups = groups
    .filter((group) => !isArchivedGroup(group))
    .sort((a, b) => {
      const aBalance = balanceMap.get(String(a.id))?.netMinor ?? 0;
      const bBalance = balanceMap.get(String(b.id))?.netMinor ?? 0;

      if (aBalance < 0 && bBalance >= 0) return -1;
      if (aBalance >= 0 && bBalance < 0) return 1;
      if (aBalance !== 0 && bBalance === 0) return -1;
      if (aBalance === 0 && bBalance !== 0) return 1;

      return Math.abs(bBalance) - Math.abs(aBalance);
    })
    .slice(0, 3);

  return activeGroups.map((group) => {
    const balance = balanceMap.get(String(group.id));
    const amount = balance?.netMinor ?? 0;
    const tone: Group['tone'] = amount < 0 ? 'negative' : 'positive';

    return {
      id: String(group.id),
      title: group.name,
      membersLabel: getMemberCountText(group.membersLabel) || group.membersLabel.replace(/\s*•\s*فعال\s*/g, '').replace(/فعال/g, '').trim(),
      statusLabel: amount < 0 ? 'شما بدهکار هستید' : amount > 0 ? 'شما طلبکار هستید' : 'تسویه شده',
      amount,
      tone,
      illustration: group.illustration,
    };
  });
}

export function DashboardPage({
  groups,
  groupBalances = [],
  balancesLoading = false,
  groupsLoading = false,
  groupsError = null,
  onCreateGroup,
  onOpenGroups,
  onOpenGroup,
  onOpenActivities,
  onOpenWallet,
}: DashboardPageProps) {
  const activeGroups = useMemo(
    () => groups.filter((group) => !isArchivedGroup(group)),
    [groups],
  );
  const groupMap = useMemo(() => getGroupById(groups), [groups]);
  const totals = useMemo(() => getDashboardTotals(groupBalances), [groupBalances]);
  const groupCards = useMemo(
    () => getGroupCards(groups, groupBalances),
    [groups, groupBalances],
  );

  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const [currentUserReady, setCurrentUserReady] = useState(false);
  const [settlementSuggestions, setSettlementSuggestions] = useState<SettlementSuggestion[]>([]);
  const [settlementsLoading, setSettlementsLoading] = useState(false);
  const [settlementsError, setSettlementsError] = useState<string | null>(null);
  const [dashboardEvents, setDashboardEvents] = useState<DashboardEvent[]>([]);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [eventsError, setEventsError] = useState<string | null>(null);
  const [busyTaskId, setBusyTaskId] = useState<string | null>(null);
  const [taskNotice, setTaskNotice] = useState<ActionNotice | null>(null);
  const [eventNotice, setEventNotice] = useState<ActionNotice | null>(null);
  const [openEventMenuId, setOpenEventMenuId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadCurrentUser() {
      try {
        const user = await getCurrentUser();

        if (!cancelled) {
          setCurrentUserId(user.id ? String(user.id) : null);
        }
      } catch (error) {
        console.warn('Could not load current user for dashboard fetches.', error);

        if (!cancelled) {
          setCurrentUserId(null);
        }
      } finally {
        if (!cancelled) {
          setCurrentUserReady(true);
        }
      }
    }

    loadCurrentUser();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!currentUserReady) return;

    let cancelled = false;

    async function loadSettlementSuggestions() {
      const balanceSuggestions = groupBalances
        .map((balance) => balanceToSuggestion(balance, groupMap.get(balance.groupId)))
        .filter((item): item is SettlementSuggestion => Boolean(item));

      if (activeGroups.length === 0) {
        setSettlementSuggestions(balanceSuggestions.slice(0, 3));
        setSettlementsLoading(false);
        setSettlementsError(null);
        return;
      }

      try {
        setSettlementsLoading(true);
        setSettlementsError(null);

        const results = await Promise.allSettled(
          activeGroups.map(async (group) => {
            const plan = await getSettlementPlan(getGroupId(group));
            return (plan.items || [])
              .map((item) => planItemToSuggestion(item, group, currentUserId, plan.updated_at || plan.created_at))
              .filter((item): item is SettlementSuggestion => Boolean(item));
          }),
        );

        if (cancelled) return;

        const planSuggestions: SettlementSuggestion[] = [];
        let hasUnexpectedError = false;

        results.forEach((result) => {
          if (result.status === 'fulfilled') {
            planSuggestions.push(...result.value);
            return;
          }

          if (!isApiError(result.reason) || result.reason.status !== 404) {
            hasUnexpectedError = true;
            console.warn('Dashboard settlement-plan request failed.', result.reason);
          }
        });

        const mergedSuggestions = mergeSuggestions(planSuggestions, balanceSuggestions);
        setSettlementSuggestions(mergedSuggestions);
        setSettlementsError(
          hasUnexpectedError && mergedSuggestions.length === 0
            ? 'فعلاً پیشنهادهای پرداخت در دسترس نیستند.'
            : null,
        );
      } finally {
        if (!cancelled) {
          setSettlementsLoading(false);
        }
      }
    }

    loadSettlementSuggestions();

    return () => {
      cancelled = true;
    };
  }, [activeGroups, currentUserId, currentUserReady, groupBalances, groupMap]);

  useEffect(() => {
    if (!currentUserReady) return;

    let cancelled = false;

    async function loadDashboardEvents() {
      try {
        setEventsLoading(true);
        setEventsError(null);

        let notificationsFailed = false;
        const notificationEvents = await getNotificationMessages({ limit: 6 })
          .then((items) => items.map(notificationToEvent))
          .catch((error) => {
            notificationsFailed = true;
            console.warn('Dashboard notification request failed.', error);
            return [] as DashboardEvent[];
          });

        const expenseResults = await Promise.allSettled(
          activeGroups.map(async (group) => {
            const expenses = await listGroupExpenses(getGroupId(group), { page_size: 5 });

            return expenses
              .filter((expense) => expense.status !== 'DELETED' && expense.status !== 'CANCELLED')
              .map((expense) => expenseToEvent(expense, group, currentUserId));
          }),
        );

        if (cancelled) return;

        const expenseEvents = expenseResults.flatMap((result) => {
          if (result.status === 'fulfilled') return result.value;

          console.warn('Dashboard expense request failed.', result.reason);
          return [];
        });

        const nextEvents = [...notificationEvents, ...expenseEvents]
          .sort((a, b) => b.createdAt - a.createdAt)
          .slice(0, 4);

        setDashboardEvents(nextEvents);
        setEventsError(
          notificationsFailed && nextEvents.length === 0
            ? 'رویدادهای اخیر دریافت نشدند.'
            : null,
        );
      } finally {
        if (!cancelled) {
          setEventsLoading(false);
        }
      }
    }

    loadDashboardEvents();

    return () => {
      cancelled = true;
    };
  }, [activeGroups, currentUserId, currentUserReady]);

  const handleNewExpenseAction = () => {
    if (activeGroups.length === 0) {
      onCreateGroup();
      return;
    }

    if (activeGroups.length === 1) {
      onOpenGroup(getGroupId(activeGroups[0]));
      return;
    }

    onOpenGroups();
  };

  function openTaskDetails(item: SettlementSuggestion) {
    if (item.groupId) onOpenGroup(item.groupId);
    else onOpenWallet();
  }

  async function handleTaskPrimary(item: SettlementSuggestion) {
    if (item.tone === 'negative') {
      openTaskDetails(item);
      return;
    }

    if (!item.itemId || String(item.status || '').toUpperCase() !== 'REPORTED') {
      openTaskDetails(item);
      return;
    }

    const confirmed = window.confirm(`مبلغ ${formatMoney(item.amount)} از گروه «${item.groupName}» را دریافت کرده‌ای؟ با تأیید تو، پرداخت برای طرف مقابل ثبت می‌شود.`);
    if (!confirmed) return;

    try {
      setBusyTaskId(item.id);
      setTaskNotice(null);
      await confirmPlanItem(item.itemId);
      setSettlementSuggestions((previous) => previous.filter((suggestion) => suggestion.id !== item.id));
      setTaskNotice({ tone: 'success', message: 'دریافت پول تأیید شد. این پرداخت برای طرف مقابل هم ثبت شد.' });
    } catch (error) {
      console.error(error);
      setTaskNotice({ tone: 'error', message: 'تأیید دریافت پول ثبت نشد. از صفحه جزئیات گروه دوباره امتحان کن.' });
    } finally {
      setBusyTaskId(null);
    }
  }

  async function handleTaskReject(item: SettlementSuggestion) {
    if (!item.itemId || String(item.status || '').toUpperCase() !== 'REPORTED') {
      openTaskDetails(item);
      return;
    }

    const confirmed = window.confirm(`مبلغ ${formatMoney(item.amount)} از گروه «${item.groupName}» را دریافت نکرده‌ای؟ با رد کردن، پرداخت برای طرف مقابل ثبت نمی‌شود.`);
    if (!confirmed) return;

    try {
      setBusyTaskId(item.id);
      setTaskNotice(null);
      await rejectPlanItem(item.itemId);
      setSettlementSuggestions((previous) => previous.filter((suggestion) => suggestion.id !== item.id));
      setTaskNotice({ tone: 'success', message: 'پرداخت رد شد. تا وقتی دوباره ثبت نشود، بدهی طرف مقابل تسویه نمی‌شود.' });
    } catch (error) {
      console.error(error);
      setTaskNotice({ tone: 'error', message: 'رد پرداخت ثبت نشد. از صفحه جزئیات گروه دوباره امتحان کن.' });
    } finally {
      setBusyTaskId(null);
    }
  }

  async function handleTaskReminder(item: SettlementSuggestion) {
    if (!item.itemId) {
      // TODO: Balance-only suggestions need a settlement-plan item id before reminders can be sent.
      setTaskNotice({ tone: 'info', message: 'فعلاً نمی‌توان برای این مورد یادآوری فرستاد.' });
      return;
    }

    try {
      setBusyTaskId(item.id);
      setTaskNotice(null);
      await sendPlanItemReminder(item.itemId);
      setTaskNotice({ tone: 'success', message: 'یادآوری پرداخت ارسال شد.' });
    } catch (error) {
      console.error(error);
      setTaskNotice({ tone: 'error', message: 'ارسال یادآوری انجام نشد؛ ممکن است اخیراً یادآوری دیگری ارسال شده باشد.' });
    } finally {
      setBusyTaskId(null);
    }
  }

  function handleTaskDispute() {
    // TODO: Connect this affordance when a dispute/report endpoint is available.
    setTaskNotice({ tone: 'info', message: 'امکان گزارش مبلغ اشتباه هنوز فعال نشده است.' });
  }

  function handleEventReport() {
    // TODO: Connect this affordance when an event error-report endpoint is available.
    setOpenEventMenuId(null);
    setEventNotice({ tone: 'info', message: 'گزارش خطای رویداد هنوز به سرویس پشتیبانی متصل نشده است.' });
  }

  function handleEventView(event: DashboardEvent) {
    setOpenEventMenuId(null);
    if (event.groupId) onOpenGroup(event.groupId);
    else onOpenActivities();
  }

  return (
    <main dir="rtl" className="app-page text-right">
      <div className="app-container app-container-dashboard space-y-5 sm:space-y-6">
        <section className="app-grid app-dashboard-top-grid">
          <BalanceHero
            creditMinor={totals.creditMinor}
            debtMinor={totals.debtMinor}
            loading={balancesLoading}
            activeGroupCount={activeGroups.length}
            onOpenWallet={onOpenWallet}
          />

          <section className="grid gap-4 sm:grid-cols-3 xl:grid-cols-1">
            <QuickActionCard
              icon={WalletCards}
              title="ثبت هزینه جدید"
              onClick={handleNewExpenseAction}
              tone="emerald"
            />
            <QuickActionCard
              icon={CreditCard}
              title="تسویه حساب"
              onClick={onOpenWallet}
              tone="amber"
            />
            <QuickActionCard
              icon={UserPlus}
              title="گروه جدید"
              onClick={onCreateGroup}
              tone="sky"
            />
          </section>
        </section>

        <section className="app-grid app-dashboard-content-grid">
          <SectionCard variant="quiet" className="p-4 sm:p-5">
            <SectionHeader
              title="کارهایی که باید انجام دهید"
              actionLabel="مشاهده همه"
              icon={<ReceiptText className="h-5 w-5 text-slate-500" />}
              onAction={onOpenWallet}
            />
            {taskNotice ? <div role="status" className={`mb-3 rounded-[14px] border px-3 py-2.5 text-xs font-bold leading-6 ${taskNotice.tone === 'success' ? 'border-emerald-100 bg-emerald-50 text-emerald-700' : taskNotice.tone === 'error' ? 'border-rose-100 bg-rose-50 text-rose-600' : 'border-sky-100 bg-sky-50 text-sky-700'}`}>{taskNotice.message}</div> : null}
            {settlementsLoading ? (
              <DashboardSectionState
                icon={ReceiptText}
                title="در حال دریافت تسویه‌ها"
                description="آخرین وضعیت پرداخت‌ها و بدهی گروه‌ها در حال آماده‌سازی است."
                loading
              />
            ) : null}
            {!settlementsLoading && settlementsError ? (
              <DashboardSectionState
                icon={AlertCircle}
                title={settlementsError}
                description="فعلاً این بخش آماده نمایش نیست. کمی بعد دوباره سر بزن."
              />
            ) : null}
            {!settlementsLoading && !settlementsError && settlementSuggestions.length === 0 ? (
              <DashboardSectionState
                icon={ReceiptText}
                title="تسویه پیشنهادی ندارید"
                description="بعد از ثبت هزینه یا محاسبه تسویه، پیشنهادهای پرداخت اینجا نمایش داده می‌شود."
              />
            ) : null}
            {!settlementsLoading && !settlementsError && settlementSuggestions.length > 0 ? (
              <div className="grid min-w-0 gap-3">
                {settlementSuggestions.map((item) => (
                  <SettlementRow
                    key={item.id}
                    item={item}
                    busy={busyTaskId === item.id}
                    onPrimary={() => void handleTaskPrimary(item)}
                    onReminder={() => void handleTaskReminder(item)}
                    onReject={() => void handleTaskReject(item)}
                    onDispute={handleTaskDispute}
                  />
                ))}
              </div>
            ) : null}
          </SectionCard>

          <SectionCard variant="quiet" className="p-4 sm:p-5">
            <SectionHeader
              title="رویدادهای اخیر"
              actionLabel="مشاهده همه"
              icon={<Bell className="h-5 w-5 text-slate-500" />}
              onAction={onOpenActivities}
            />
            {eventNotice ? <div role="status" className="mb-3 rounded-[14px] border border-sky-100 bg-sky-50 px-3 py-2.5 text-xs font-bold leading-6 text-sky-700">{eventNotice.message}</div> : null}
            {eventsLoading ? (
              <DashboardSectionState
                icon={Bell}
                title="در حال دریافت رویدادها"
                description="اعلان‌ها و آخرین هزینه‌های گروه‌ها در حال آماده‌سازی است."
                loading
              />
            ) : null}
            {!eventsLoading && eventsError ? (
              <DashboardSectionState
                icon={AlertCircle}
                title={eventsError}
                description="فعلاً این بخش آماده نمایش نیست. کمی بعد دوباره سر بزن."
              />
            ) : null}
            {!eventsLoading && !eventsError && dashboardEvents.length === 0 ? (
              <DashboardSectionState
                icon={Bell}
                title="رویدادی برای نمایش نیست"
                description="بعد از ثبت هزینه، تسویه یا اعلان جدید، آخرین رویدادها اینجا می‌آیند."
              />
            ) : null}
            {!eventsLoading && !eventsError && dashboardEvents.length > 0 ? (
              <div className="grid min-w-0 gap-3">
                {dashboardEvents.map((event) => (
                  <EventRow
                    key={event.id}
                    event={event}
                    menuOpen={openEventMenuId === event.id}
                    onToggleMenu={() => setOpenEventMenuId((current) => current === event.id ? null : event.id)}
                    onView={() => handleEventView(event)}
                    onReport={handleEventReport}
                  />
                ))}
              </div>
            ) : null}
          </SectionCard>
        </section>

        <SectionCard variant="quiet" className="p-4 sm:p-5">
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Users className="h-5 w-5 text-slate-700" />
              <h2 className="text-lg font-black text-text sm:text-xl">گروه‌ها</h2>
            </div>
            <button
              type="button"
              onClick={onOpenGroups}
              className="dashboard-section-action inline-flex min-h-9 items-center rounded-full px-3 text-xs font-extrabold text-emerald-600 transition hover:bg-emerald-50/60 hover:text-emerald-700"
            >
              مشاهده همه گروه‌ها
            </button>
          </div>

          {groupsLoading ? (
            <div className="dashboard-panel-state rounded-2xl border border-dashed border-slate-200/90 bg-white/85 p-6 text-center text-sm font-bold text-muted shadow-[0_10px_24px_rgba(15,23,42,0.055)]">
              <Loader2 className="mx-auto mb-3 h-5 w-5 animate-spin text-slate-500" />
              در حال دریافت گروه‌ها...
            </div>
          ) : null}

          {!groupsLoading && groupsError ? (
            <div className="dashboard-panel-error rounded-2xl border border-rose-200/80 bg-rose-50 p-6 text-center text-sm font-bold text-rose-600 shadow-[0_10px_24px_rgba(15,23,42,0.055)]">
              {groupsError}
            </div>
          ) : null}

          {!groupsLoading && !groupsError && groupCards.length === 0 ? (
            <div className="dashboard-panel-empty rounded-2xl border border-dashed border-emerald-200 bg-white/85 p-7 text-center shadow-[0_10px_24px_rgba(15,23,42,0.055)]">
              <Users className="mx-auto mb-3 h-7 w-7 text-emerald-600" />
              <h3 className="text-base font-black text-text">هنوز گروه فعالی ندارید</h3>
              <button
                type="button"
                onClick={onCreateGroup}
                className="mt-5 inline-flex h-11 items-center justify-center gap-2 rounded-2xl bg-emerald-600 px-5 text-sm font-bold text-white transition hover:bg-emerald-700"
              >
                <Plus className="h-4 w-4" />
                ساخت گروه جدید
              </button>
            </div>
          ) : null}

          {!groupsLoading && !groupsError && groupCards.length > 0 ? (
            <div className="grid min-w-0 gap-4 lg:grid-cols-3">
              {groupCards.map((group) => (
                <DashboardGroupCard
                  key={group.id}
                  id={group.id}
                  title={group.title}
                  membersLabel={group.membersLabel}
                  statusLabel={group.statusLabel}
                  amount={group.amount}
                  tone={group.tone}
                  illustration={group.illustration}
                  onOpen={onOpenGroup}
                />
              ))}
            </div>
          ) : null}
        </SectionCard>
      </div>
    </main>
  );
}
