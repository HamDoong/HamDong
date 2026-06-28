import { useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  Archive,
  ArrowLeft,
  Banknote,
  Check,
  Copy,
  Eye,
  HandCoins,
  Link2,
  Loader2,
  LogOut,
  Plus,
  ReceiptText,
  RefreshCw,
  RotateCcw,
  Save,
  Settings,
  Trash2,
  Upload,
  UserMinus,
  Users,
  X,
} from 'lucide-react';
import { InlineLoader, useFeedback } from '../components/feedback/FeedbackProvider';
import { isApiError } from '../lib/api';
import { uploadReceipt, openMediaFile } from '../lib/mediaApi';
import { getFriendlyApiErrorMessage, humanizeMachineLabel } from '../lib/userMessages';
import {
  createGroupExpense,
  deleteExpense,
  listGroupExpenses,
  type BackendExpense,
  type ExpenseSplitMethod,
  type FeeType,
} from '../lib/expenseApi';
import {
  activateSettlementPlan,
  cancelSettlement,
  confirmPlanItem,
  confirmSettlement,
  createGroupSettlement,
  generateSettlementPlan,
  getGroupBalances,
  getMyGroupBalance,
  getSettlementPlan,
  listGroupSettlements,
  rejectPlanItem,
  rejectSettlement,
  reportPlanItemPaid,
  type BalanceItem,
  type MyBalanceResponse,
  type SettlementItem,
  type SettlementPlan,
  type SettlementPlanItem,
} from '../lib/settlementApi';
import {
  archiveGroup,
  createGroupInvite,
  getBackendGroupMemberId,
  getBackendGroupMemberName,
  getBackendGroupMemberPhone,
  getBackendGroupMemberUserId,
  getGroupDetail,
  getGroupMembers,
  getInviteId,
  getInviteUrl,
  leaveGroup,
  removeGroupMember,
  restoreGroup,
  revokeGroupInvite,
  updateGroup,
  type BackendGroup,
  type BackendGroupMember,
  type BackendGroupType,
  type CreatedInvite,
} from '../lib/groupApi';
import { MoneyWithWords } from '../lib/money';
import { getCurrentUser, type CurrentUser } from '../lib/userApi';

interface GroupDetailPageProps {
  groupId: string;
  onBack: () => void;
  onGroupUpdated: (group: BackendGroup) => void;
  onGroupRemoved: (groupId: string) => void;
}

type ModalName = 'expense' | 'settlement' | 'settings' | 'activity' | null;
type ManualPaymentMode = 'FULL' | 'PARTIAL';

function cn(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(' ');
}

function toPersianNumber(value: string | number) {
  return String(value).replace(/\d/g, (digit) => '۰۱۲۳۴۵۶۷۸۹'[Number(digit)]);
}

function normalizeDigits(value: string) {
  const persianDigits = '۰۱۲۳۴۵۶۷۸۹';
  const arabicDigits = '٠١٢٣٤٥٦٧٨٩';

  return value
    .replace(/[۰-۹]/g, (digit) => String(persianDigits.indexOf(digit)))
    .replace(/[٠-٩]/g, (digit) => String(arabicDigits.indexOf(digit)));
}

function parseAmountToMinor(value: string) {
  const digits = normalizeDigits(value).replace(/[^0-9]/g, '');
  return Number(digits || 0);
}

function parsePercentage(value: string) {
  const normalized = normalizeDigits(value).replace(/٫/g, '.').replace(/,/g, '.');
  const numeric = Number(normalized.replace(/[^0-9.]/g, ''));
  return Number.isFinite(numeric) && numeric > 0 ? numeric : 0;
}

function formatMoney(minor = 0) {
  const absValue = Math.abs(Math.round(minor));
  return `${toPersianNumber(absValue.toLocaleString('en-US'))} تومان`;
}

function formatSignedMoney(minor = 0) {
  return formatMoney(minor);
}

function toPersianDate(value?: string) {
  if (!value) return 'بدون تاریخ';

  try {
    return new Intl.DateTimeFormat('fa-IR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function getBackendMessage(error: unknown) {
  return getFriendlyApiErrorMessage(error, {
    defaultMessage: 'عملیات انجام نشد. لطفاً دوباره تلاش کن.',
    invalidMessage: 'اطلاعات واردشده کامل یا درست نیست.',
  });
}

function getMemberId(member: BackendGroupMember) {
  return getBackendGroupMemberId(member);
}

function getMemberUserId(member: BackendGroupMember) {
  return getBackendGroupMemberUserId(member);
}

function getMemberName(member: BackendGroupMember) {
  return getBackendGroupMemberName(member);
}

function getMemberPhone(member: BackendGroupMember) {
  return getBackendGroupMemberPhone(member);
}

function getRoleLabel(role?: string) {
  if (role === 'OWNER') return 'مالک';
  if (role === 'ADMIN') return 'مدیر';
  if (role === 'MEMBER') return 'عضو';
  return role || 'عضو';
}

function getCurrentUserId(user: CurrentUser | null) {
  return user?.id ? String(user.id) : '';
}

function getExpenseTotal(expense: BackendExpense) {
  return (
    expense.total_amount_minor ??
    (expense.base_amount_minor || 0) +
      (expense.tax_amount_minor || 0) +
      (expense.service_fee_amount_minor || 0)
  );
}

function getSettlementStatusLabel(status?: string) {
  if (!status) return 'نامشخص';
  if (status === 'PENDING') return 'در انتظار';
  if (status === 'REPORTED') return 'گزارش پرداخت';
  if (status === 'CONFIRMED') return 'تأیید شده';
  if (status === 'REJECTED') return 'رد شده';
  if (status === 'CANCELLED') return 'لغو شده';
  if (status === 'ACTIVE') return 'فعال';
  if (status === 'DRAFT') return 'آماده';
  if (status === 'COMPLETED') return 'تکمیل شده';
  if (status === 'PENDING_CONFIRMATION') return 'در انتظار تأیید';
  if (status === 'EXPIRED') return 'منقضی شده';
  return humanizeMachineLabel(status, 'نامشخص');
}

function isOpenSettlementStatus(status?: string) {
  return !status || ['PENDING', 'PENDING_CONFIRMATION', 'REPORTED', 'ACTIVE', 'DRAFT'].includes(status);
}

function canReportPlanItem(item: SettlementPlanItem, plan?: SettlementPlan | null) {
  return plan?.status === 'ACTIVE' && ['PENDING', 'REJECTED'].includes(item.status || 'PENDING');
}

function canReviewPlanItem(item: SettlementPlanItem) {
  return item.status === 'REPORTED';
}

const dashboardCard =
  'dashboard-section-card rounded-[24px] border border-emerald-100/80 bg-white/95 text-text shadow-[0_18px_44px_rgba(15,23,42,0.075)] backdrop-blur dark:border-emerald-500/20 dark:bg-slate-950/90 dark:text-slate-100';

const dashboardQuietCard =
  'dashboard-section-card dashboard-section-card--quiet rounded-[24px] border border-emerald-100/70 bg-white/[0.90] text-text shadow-[0_12px_32px_rgba(15,23,42,0.055)] backdrop-blur dark:border-emerald-500/15 dark:bg-slate-950/80 dark:text-slate-100';

const dashboardRow =
  'dashboard-list-row dashboard-list-card rounded-[22px] border border-emerald-100/80 bg-white/[0.92] text-right text-text shadow-[0_8px_22px_rgba(15,23,42,0.035)] transition hover:-translate-y-0.5 hover:border-emerald-200 hover:bg-white hover:shadow-[0_14px_32px_rgba(15,23,42,0.07)] dark:border-emerald-500/15 dark:bg-slate-900/80 dark:text-slate-100 dark:hover:border-emerald-400/30 dark:hover:bg-slate-900';

const controlRadius = 'rounded-[18px]';

const inputClass =
  'h-12 w-full rounded-[18px] border border-emerald-200/90 bg-white/90 px-4 text-right text-sm font-bold text-text outline-none transition placeholder:text-slate-400 focus:border-emerald-400 focus:bg-white focus:ring-4 focus:ring-emerald-500/10 disabled:bg-slate-50 disabled:text-slate-400 dark:border-emerald-500/20 dark:bg-slate-900/80 dark:text-slate-100 dark:placeholder:text-slate-500 dark:focus:border-emerald-400/50 dark:focus:bg-slate-900 dark:disabled:bg-slate-900/50 dark:disabled:text-slate-500';

const textareaClass =
  'min-h-[96px] w-full resize-none rounded-[18px] border border-emerald-200/90 bg-white/90 px-4 py-3 text-right text-sm font-semibold leading-7 text-text outline-none transition placeholder:text-slate-400 focus:border-emerald-400 focus:bg-white focus:ring-4 focus:ring-emerald-500/10 disabled:bg-slate-50 disabled:text-slate-400 dark:border-emerald-500/20 dark:bg-slate-900/80 dark:text-slate-100 dark:placeholder:text-slate-500 dark:focus:border-emerald-400/50 dark:focus:bg-slate-900 dark:disabled:bg-slate-900/50 dark:disabled:text-slate-500';

const scrollAreaClass =
  'min-h-0 overflow-y-auto overscroll-auto pl-1 pr-0 [scrollbar-width:thin] [scrollbar-color:rgba(16,185,129,0.45)_transparent] dark:[scrollbar-color:rgba(52,211,153,0.35)_transparent]';

function readDisplayString(value: unknown) {
  return typeof value === 'string' ? value.trim() : '';
}

function isEmailLikeValue(value?: string) {
  return Boolean(value && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value));
}

function pickUserFacingName(...values: unknown[]) {
  return values.map(readDisplayString).find((value) => value && !isEmailLikeValue(value)) || '';
}

function getMemberPreferredDisplayName(member?: BackendGroupMember) {
  if (!member) return '';

  return (
    pickUserFacingName(
      member.art_name,
      member.username,
      member.display_name,
      member.display_name_snapshot,
      member.full_name,
      member.name,
      [member.first_name, member.last_name].filter(Boolean).join(' '),
      member.user?.art_name,
      member.user?.username,
      member.user?.display_name,
      member.user?.full_name,
      member.user?.name,
      [member.user?.first_name, member.user?.last_name].filter(Boolean).join(' '),
      member.profile?.art_name,
      member.profile?.username,
      member.profile?.display_name,
      member.member?.art_name,
      member.member?.username,
      member.member?.display_name,
    ) || getMemberName(member)
  );
}

function getUserDisplayFromId(userId: string, members: BackendGroupMember[]) {
  const member = members.find((item) => getMemberUserId(item) === userId);
  return getMemberPreferredDisplayName(member) || 'عضو گروه';
}

function getBalanceDisplayName(balance: BalanceItem, members: BackendGroupMember[]) {
  const memberName = getUserDisplayFromId(balance.user_id, members);
  const balanceRecord = balance as BalanceItem & { username?: string; name?: string; full_name?: string };

  return (
    memberName ||
    pickUserFacingName(
      balanceRecord.art_name,
      balanceRecord.username,
      balanceRecord.display_name,
      balanceRecord.full_name,
      balanceRecord.name,
      balanceRecord.phone_number,
    ) ||
    'عضو گروه'
  );
}

function getDebtPartyName(userId: string, members: BackendGroupMember[]) {
  return getUserDisplayFromId(userId, members);
}

function getPlanPartyName(
  item: SettlementPlanItem,
  type: 'payer' | 'receiver',
  members: BackendGroupMember[],
) {
  if (type === 'payer') {
    return (
      item.payer_display_name ||
      item.payer_art_name ||
      getUserDisplayFromId(item.payer_user_id, members)
    );
  }

  return (
    item.receiver_display_name ||
    item.receiver_art_name ||
    getUserDisplayFromId(item.receiver_user_id, members)
  );
}

interface OptimizedSettlementSuggestion {
  id: string;
  payer_user_id: string;
  payerName: string;
  receiver_user_id: string;
  receiverName: string;
  amount_minor: number;
}

function calculateOptimizedSettlements(
  balances: BalanceItem[],
  members: BackendGroupMember[],
): OptimizedSettlementSuggestion[] {
  const debtors = balances
    .map((balance) => ({
      userId: balance.user_id,
      name: getBalanceDisplayName(balance, members),
      amount: Math.max(0, Math.round(Math.abs(Math.min(balance.net_balance_minor || 0, 0)))),
    }))
    .filter((item) => item.userId && item.amount > 0)
    .sort((a, b) => b.amount - a.amount);

  const creditors = balances
    .map((balance) => ({
      userId: balance.user_id,
      name: getBalanceDisplayName(balance, members),
      amount: Math.max(0, Math.round(Math.max(balance.net_balance_minor || 0, 0))),
    }))
    .filter((item) => item.userId && item.amount > 0)
    .sort((a, b) => b.amount - a.amount);

  const suggestions: OptimizedSettlementSuggestion[] = [];
  let debtorIndex = 0;
  let creditorIndex = 0;

  while (debtorIndex < debtors.length && creditorIndex < creditors.length) {
    const debtor = debtors[debtorIndex];
    const creditor = creditors[creditorIndex];
    const amount = Math.min(debtor.amount, creditor.amount);

    if (amount > 0 && debtor.userId !== creditor.userId) {
      suggestions.push({
        id: `optimized-${debtor.userId}-${creditor.userId}-${suggestions.length}`,
        payer_user_id: debtor.userId,
        payerName: debtor.name,
        receiver_user_id: creditor.userId,
        receiverName: creditor.name,
        amount_minor: amount,
      });
    }

    debtor.amount -= amount;
    creditor.amount -= amount;

    if (debtor.amount <= 0) debtorIndex += 1;
    if (creditor.amount <= 0) creditorIndex += 1;
  }

  return suggestions;
}

function getSettlementErrorTitle(action: 'create' | 'plan' | 'item' | 'review') {
  if (action === 'create') return 'پرداخت ثبت نشد';
  if (action === 'plan') return 'محاسبه تسویه انجام نشد';
  if (action === 'item') return 'وضعیت پرداخت تغییر نکرد';
  return 'تأیید پرداخت انجام نشد';
}

function getSettlementErrorDescription(error: unknown) {
  const message = getBackendMessage(error);
  const normalized = message.toLowerCase();

  if (normalized.includes('403') || normalized.includes('permission') || normalized.includes('forbidden')) {
    return 'برای انجام این کار دسترسی نداری یا عضو این گروه نیستی.';
  }

  if (normalized.includes('404') || normalized.includes('not found')) {
    return 'این پرداخت یا گروه پیدا نشد. صفحه را بروزرسانی کن و دوباره تلاش کن.';
  }

  if (normalized.includes('amount') || normalized.includes('مبلغ')) {
    return 'مبلغ پرداخت را دقیق و به عدد وارد کن.';
  }

  if (normalized.includes('receiver') || normalized.includes('دریافت')) {
    return 'دریافت‌کننده معتبر نیست. یکی از اعضای گروه را انتخاب کن.';
  }

  return message || 'اتصال یا اطلاعات پرداخت مشکل دارد. صفحه را بروزرسانی کن و دوباره تلاش کن.';
}

type VisualTone = 'positive' | 'negative' | 'warning' | 'sky' | 'slate' | 'neutral';
type QuickSection = 'expenses' | 'settlement' | 'settings' | 'members' | 'activity';

function getMyAccountStatus(amount: number) {
  if (amount > 0) {
    return {
      label: 'بدهکار',
      amount: formatSignedMoney(amount),
      tone: 'negative' as VisualTone,
    };
  }

  if (amount < 0) {
    return {
      label: 'طلبکار',
      amount: formatSignedMoney(amount),
      tone: 'positive' as VisualTone,
    };
  }

  return {
    label: 'تسویه',
    amount: formatSignedMoney(amount),
    tone: 'slate' as VisualTone,
  };
}

function getRemainingPaymentsLabel(count: number) {
  return count > 0 ? `${toPersianNumber(count)} پرداخت` : 'بدون پرداخت';
}

function scrollToSection(id: QuickSection) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function MemberAvatar({ name, owner = false }: { name: string; owner?: boolean }) {
  return (
    <div
      className={cn(
        'flex h-11 w-11 shrink-0 items-center justify-center rounded-full border-2 text-sm font-black shadow-[inset_3px_0_0_#10B981,0_10px_28px_rgba(15,23,42,0.045)]',
        owner
          ? 'border-orange-300 bg-orange-50 text-orange-700'
          : 'border-emerald-100 bg-gradient-to-br from-emerald-50 via-teal-50 to-white text-emerald-700',
      )}
    >
      {name.slice(0, 1) || '؟'}
    </div>
  );
}

function toneCardClass(tone: VisualTone) {
  if (tone === 'positive') {
    return 'border-2 border-emerald-200/80 bg-gradient-to-l from-white via-emerald-50/85 to-emerald-50/70 text-emerald-700 shadow-[inset_3px_0_0_#10B981,0_18px_44px_rgba(16,185,129,0.075)]';
  }

  if (tone === 'negative') {
    return 'border-2 border-rose-200/80 bg-gradient-to-l from-white via-rose-50/85 to-rose-50/70 text-rose-600 shadow-[inset_3px_0_0_#F43F5E,0_18px_44px_rgba(244,63,94,0.07)]';
  }

  if (tone === 'warning') {
    return 'border-2 border-orange-200/80 bg-gradient-to-l from-white via-orange-50/85 to-orange-50/70 text-orange-700 shadow-[inset_3px_0_0_#F97316,0_18px_44px_rgba(249,115,22,0.07)]';
  }

  if (tone === 'sky') {
    return 'border-2 border-sky-200/80 bg-gradient-to-l from-white via-sky-50/85 to-sky-50/70 text-sky-700 shadow-[inset_3px_0_0_#0EA5E9,0_18px_44px_rgba(14,165,233,0.065)]';
  }

  if (tone === 'slate') {
    return 'border-2 border-slate-200 bg-gradient-to-l from-white via-slate-50/90 to-white text-slate-700 shadow-[inset_3px_0_0_#64748B,0_18px_44px_rgba(15,23,42,0.055)]';
  }

  return 'border-2 border-emerald-100/80 bg-white/[0.88] text-slate-700 shadow-[0_16px_38px_rgba(15,23,42,0.045)]';
}

function iconToneClass(tone: VisualTone) {
  if (tone === 'positive') return 'bg-emerald-600 text-white shadow-[0_12px_28px_rgba(16,185,129,0.16)]';
  if (tone === 'negative') return 'bg-rose-500 text-white shadow-[0_12px_28px_rgba(244,63,94,0.14)]';
  if (tone === 'warning') return 'bg-orange-500 text-white shadow-[0_12px_28px_rgba(249,115,22,0.14)]';
  if (tone === 'sky') return 'bg-sky-500 text-white shadow-[0_12px_28px_rgba(14,165,233,0.14)]';
  if (tone === 'slate') return 'bg-slate-700 text-white shadow-[0_12px_28px_rgba(15,23,42,0.10)]';
  return 'bg-white text-emerald-600 shadow-sm';
}

function SectionCard({
  id,
  title,
  icon,
  badge,
  children,
  accent = 'emerald',
}: {
  id?: string;
  title: string;
  icon?: ReactNode;
  badge?: ReactNode;
  children: ReactNode;
  accent?: 'emerald' | 'sky' | 'orange' | 'slate';
}) {
  const accentClass =
    accent === 'sky'
      ? 'border-sky-100/90 shadow-[0_20px_52px_rgba(14,165,233,0.055)]'
      : accent === 'orange'
        ? 'border-orange-100/90 shadow-[0_20px_52px_rgba(249,115,22,0.055)]'
        : accent === 'slate'
          ? 'border-slate-200 shadow-[0_20px_52px_rgba(15,23,42,0.045)]'
          : 'border-emerald-100/90 shadow-[0_20px_52px_rgba(15,23,42,0.055)]';

  const iconClass =
    accent === 'sky'
      ? 'bg-sky-50 text-sky-600 shadow-[inset_3px_0_0_#0EA5E9]'
      : accent === 'orange'
        ? 'bg-orange-50 text-orange-600 shadow-[inset_3px_0_0_#F97316]'
        : accent === 'slate'
          ? 'bg-slate-50 text-slate-600 shadow-[inset_3px_0_0_#64748B]'
          : 'bg-emerald-50 text-emerald-600 shadow-[inset_3px_0_0_#10B981]';

  return (
    <section
      id={id}
      className={cn(
        'scroll-mt-6 rounded-[28px] border-2 bg-white/95 p-5 backdrop-blur sm:p-6',
        accentClass,
      )}
    >
      <div className="mb-5 flex items-center justify-between gap-4 border-b-2 border-emerald-50/70 pb-4">
        <div className="text-right">
          <h2 className="text-xl font-black text-text sm:text-2xl">{title}</h2>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {badge}
          {icon ? (
            <div className={cn('flex h-12 w-12 items-center justify-center rounded-[18px]', iconClass)}>
              {icon}
            </div>
          ) : null}
        </div>
      </div>

      {children}
    </section>
  );
}

function HeaderMiniCard({
  label,
  value,
  status,
  tone = 'neutral',
  icon,
}: {
  label: string;
  value: string;
  status?: string;
  tone?: 'neutral' | 'positive' | 'negative';
  icon: ReactNode;
}) {
  const visualTone: VisualTone =
    tone === 'positive' ? 'positive' : tone === 'negative' ? 'negative' : 'slate';

  return (
    <div className={cn('rounded-[22px] px-4 py-3 text-right', toneCardClass(visualTone))}>
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-xs font-black opacity-70">{label}</div>
          {status ? <div className="mt-1 text-sm font-black">{status}</div> : null}
          <div className="mt-1 text-lg font-black tracking-[-0.02em]">{value}</div>
        </div>

        <span className={cn('flex h-10 w-10 shrink-0 items-center justify-center rounded-[16px]', iconToneClass(visualTone))}>
          {icon}
        </span>
      </div>
    </div>
  );
}

function AccountStatusBox({ amount }: { amount: number }) {
  const status = getMyAccountStatus(amount);

  return (
    <div className={cn('rounded-[24px] p-4 text-right', toneCardClass(status.tone))}>
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-black">حساب من</div>
          <div className="mt-1 text-xs font-bold opacity-75">وضعیت تو در این گروه</div>
        </div>

        <span className={cn('flex h-10 w-10 shrink-0 items-center justify-center rounded-[16px]', iconToneClass(status.tone))}>
          <HandCoins className="h-4 w-4" />
        </span>
      </div>

      <div className="text-2xl font-black tracking-[-0.03em]">{status.label}</div>
      <div className="mt-2 text-lg font-black">{status.amount}</div>
    </div>
  );
}

function RemainingPaymentsBox({
  count,
  totalMinor,
  tone = 'slate',
}: {
  count: number;
  totalMinor: number;
  tone?: VisualTone;
}) {
  const hasPayments = count > 0;

  return (
    <div className={cn('rounded-[24px] p-4 text-right', toneCardClass(tone))}>
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-black">پرداخت‌های مانده</div>
          <div className="mt-1 text-xs font-bold opacity-75">
            {hasPayments ? 'جمع پرداخت‌های باقی‌مانده' : 'چیزی باقی نمانده.'}
          </div>
        </div>

        <span className={cn('flex h-10 w-10 shrink-0 items-center justify-center rounded-[16px]', iconToneClass(tone))}>
          <ReceiptText className="h-4 w-4" />
        </span>
      </div>

      <div className="text-2xl font-black tracking-[-0.03em]">
        {getRemainingPaymentsLabel(count)}
      </div>

      <div className="mt-2 text-lg font-black">
        {hasPayments ? formatMoney(totalMinor) : formatMoney(0)}
      </div>
    </div>
  );
}

function EmptyState({ title, description, icon }: { title: string; description: string; icon?: ReactNode }) {
  return (
    <div className="rounded-[22px] border-2 border-dashed border-emerald-100/80 bg-white/[0.58] p-7 text-center shadow-[0_16px_38px_rgba(15,23,42,0.035)]">
      <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-[18px] bg-white text-emerald-600 shadow-sm">
        {icon ?? <Users className="h-6 w-6" />}
      </div>

      <h3 className="text-lg font-black text-text">{title}</h3>

      <p className="mx-auto mt-2 max-w-[420px] text-sm font-semibold leading-7 text-muted">
        {description}
      </p>
    </div>
  );
}

function QuickActionButton({
  id,
  label,
  icon,
  tone = 'emerald',
}: {
  id: QuickSection;
  label: string;
  icon: ReactNode;
  tone?: 'emerald' | 'sky' | 'orange' | 'slate';
}) {
  const toneClass =
    tone === 'sky'
      ? 'border-sky-200/90 bg-gradient-to-l from-white via-sky-50/90 to-sky-50/70 text-sky-700 shadow-[inset_3px_0_0_#0EA5E9,0_16px_36px_rgba(14,165,233,0.055)] hover:border-sky-300'
      : tone === 'orange'
        ? 'border-orange-200/90 bg-gradient-to-l from-white via-orange-50/90 to-orange-50/70 text-orange-700 shadow-[inset_3px_0_0_#F97316,0_16px_36px_rgba(249,115,22,0.055)] hover:border-orange-300'
        : tone === 'slate'
          ? 'border-slate-200 bg-gradient-to-l from-white via-slate-50 to-white text-slate-700 shadow-[inset_3px_0_0_#64748B,0_16px_36px_rgba(15,23,42,0.04)] hover:border-slate-300'
          : 'border-emerald-200/90 bg-gradient-to-l from-white via-emerald-50/90 to-emerald-50/70 text-emerald-700 shadow-[inset_3px_0_0_#10B981,0_16px_36px_rgba(16,185,129,0.055)] hover:border-emerald-300';

  return (
    <button
      type="button"
      onClick={() => scrollToSection(id)}
      className={cn(
        'inline-flex h-[76px] w-full flex-col items-center justify-center gap-1.5 rounded-[20px] border-2 px-4 text-sm font-black transition hover:-translate-y-0.5 hover:shadow-[0_20px_44px_rgba(15,23,42,0.07)]',
        toneClass,
      )}
    >
      <span className="flex h-5 w-5 items-center justify-center">
        {icon}
      </span>
      <span>{label}</span>
    </button>
  );
}

function Button({
  children,
  onClick,
  disabled,
  tone = 'primary',
  className,
  type = 'button',
}: {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  tone?: 'primary' | 'secondary' | 'danger' | 'dark' | 'ghost';
  className?: string;
  type?: 'button' | 'submit';
}) {
  const toneClass =
    tone === 'primary'
      ? 'bg-emerald-600 text-white shadow-[0_14px_32px_rgba(16,185,129,0.22)] ring-1 ring-emerald-500/20 hover:-translate-y-0.5 hover:bg-emerald-700 dark:bg-emerald-500 dark:text-white dark:hover:bg-emerald-400'
      : tone === 'danger'
        ? 'border border-rose-200 bg-rose-50 text-rose-600 hover:bg-rose-100 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-200 dark:hover:bg-rose-500/15'
        : tone === 'dark'
          ? 'bg-slate-900 text-white hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-950 dark:hover:bg-white'
          : tone === 'ghost'
            ? 'bg-transparent text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
            : 'border border-emerald-200 bg-emerald-50/80 text-emerald-700 shadow-[0_10px_24px_rgba(15,23,42,0.045)] hover:-translate-y-0.5 hover:border-emerald-300 hover:bg-emerald-50 dark:border-emerald-500/25 dark:bg-emerald-500/10 dark:text-emerald-200 dark:hover:border-emerald-400/40 dark:hover:bg-emerald-500/15';

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'inline-flex min-h-11 items-center justify-center gap-2 px-4 text-sm font-black transition disabled:cursor-not-allowed disabled:opacity-55 disabled:hover:translate-y-0',
        controlRadius,
        toneClass,
        className,
      )}
    >
      {children}
    </button>
  );
}

function ActionButton({
  children,
  onClick,
  disabled,
  tone = 'primary',
  className,
  type = 'button',
}: {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  tone?: 'primary' | 'secondary' | 'danger' | 'dark' | 'ghost';
  className?: string;
  type?: 'button' | 'submit';
}) {
  const toneClass =
    tone === 'primary'
      ? 'bg-emerald-600 text-white shadow-[0_14px_32px_rgba(16,185,129,0.22)] ring-1 ring-emerald-500/20 hover:-translate-y-0.5 hover:bg-emerald-700 dark:bg-emerald-500 dark:text-white dark:hover:bg-emerald-400'
      : tone === 'danger'
        ? 'border border-rose-200 bg-rose-50 text-rose-600 hover:bg-rose-100 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-200 dark:hover:bg-rose-500/15'
        : tone === 'dark'
          ? 'bg-slate-900 text-white hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-950 dark:hover:bg-white'
          : tone === 'ghost'
            ? 'bg-transparent text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
            : 'border border-emerald-200 bg-emerald-50/80 text-emerald-700 shadow-[0_10px_24px_rgba(15,23,42,0.045)] hover:-translate-y-0.5 hover:border-emerald-300 hover:bg-emerald-50 dark:border-emerald-500/25 dark:bg-emerald-500/10 dark:text-emerald-200 dark:hover:border-emerald-400/40 dark:hover:bg-emerald-500/15';

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'inline-flex min-h-11 items-center justify-center gap-2 px-4 text-sm font-black transition disabled:cursor-not-allowed disabled:opacity-55 disabled:hover:translate-y-0',
        controlRadius,
        toneClass,
        className,
      )}
    >
      {children}
    </button>
  );
}

function Modal({
  open,
  title,
  description,
  icon,
  children,
  onClose,
  size = 'md',
}: {
  open: boolean;
  title: string;
  description?: string;
  icon?: ReactNode;
  children: ReactNode;
  onClose: () => void;
  size?: 'md' | 'lg';
}) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/36 px-3 py-3 backdrop-blur-sm sm:items-center dark:bg-black/55"
      dir="rtl"
    >
      <div
        className={cn(
          'max-h-[92vh] w-full overflow-hidden rounded-[32px] border border-white/90 bg-white text-right text-text shadow-[0_28px_90px_rgba(15,23,42,0.18)] dark:border-emerald-500/15 dark:bg-slate-950 dark:text-slate-100 dark:shadow-[0_28px_90px_rgba(0,0,0,0.45)]',
          size === 'lg' ? 'max-w-[900px]' : 'max-w-[620px]',
        )}
      >
        <div className="flex items-start justify-between gap-4 border-b border-emerald-100/70 bg-white/[0.45] px-4 py-4 sm:px-5 dark:border-emerald-500/15 dark:bg-slate-900/60">
          <div className="flex min-w-0 items-start gap-3 text-right">
            {icon ? (
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[18px] bg-emerald-50 text-emerald-600 shadow-[inset_3px_0_0_#10B981] dark:bg-emerald-500/10 dark:text-emerald-300 dark:shadow-[inset_3px_0_0_#34D399]">
                {icon}
              </span>
            ) : null}

            <div className="min-w-0 text-right">
              <h2 className="text-xl font-black tracking-[-0.03em] text-text dark:text-slate-100">{title}</h2>
              {description ? (
                <p className="mt-1 text-sm font-bold leading-6 text-muted dark:text-slate-400">{description}</p>
              ) : null}
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[18px] bg-slate-50 text-slate-500 transition hover:bg-rose-50 hover:text-rose-600 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-rose-500/10 dark:hover:text-rose-200"
            aria-label="بستن"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="max-h-[calc(92vh-92px)] overflow-y-auto px-4 py-4 text-right sm:px-5">{children}</div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block text-right">
      <span className="mb-2 block text-sm font-black text-text dark:text-slate-100">{label}</span>
      {children}
    </label>
  );
}

function MetaTags({ user, date }: { user: string; date: string }) {
  return (
    <div className="mt-2 flex flex-wrap items-center justify-start gap-2 text-right text-xs font-semibold text-muted dark:text-slate-400">
      <span className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 dark:border-slate-700 dark:bg-slate-800/80 dark:text-slate-300">
        {user}
      </span>

      <span className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 dark:border-slate-700 dark:bg-slate-800/80 dark:text-slate-300">
        {date}
      </span>
    </div>
  );
}

function MiniNumberCard({
  label,
  value,
  tone,
  signed = false,
}: {
  label: string;
  value: number | string | null | undefined;
  tone: 'rose' | 'emerald' | 'slate';
  signed?: boolean;
}) {
  const classes =
    tone === 'rose'
      ? 'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-200'
      : tone === 'emerald'
        ? 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-200'
        : 'border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-800/80 dark:text-slate-200';

  return (
    <div className={cn('rounded-[20px] border px-4 py-3 text-right', classes)}>
      <p className="text-xs font-extrabold opacity-75">{label}</p>
      <div className="mt-1">
        <MoneyWithWords
          amount={value}
          signed={signed}
          className="min-w-0"
          valueClassName="truncate text-lg font-black"
          textClassName="mt-1 text-[10px] font-semibold opacity-70"
          showText={true}
        />
      </div>
    </div>
  );
}

function SectionHeader({ title, action }: { title: string; action?: ReactNode }) {
  return (
    <div className="dashboard-section-header mb-4 flex flex-wrap items-center justify-between gap-3 rounded-[20px] border border-transparent p-0 text-right">
      <h2 className="text-lg font-black tracking-[-0.02em] text-text dark:text-slate-100">{title}</h2>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

export function GroupDetailPage({
  groupId,
  onBack,
  onGroupUpdated,
  onGroupRemoved,
}: GroupDetailPageProps) {
  const { notify, confirm } = useFeedback();

  const [modal, setModal] = useState<ModalName>(null);
  const [showAdvancedExpense, setShowAdvancedExpense] = useState(false);

  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [group, setGroup] = useState<BackendGroup | null>(null);
  const [members, setMembers] = useState<BackendGroupMember[]>([]);
  const [expenses, setExpenses] = useState<BackendExpense[]>([]);
  const [balances, setBalances] = useState<BalanceItem[]>([]);
  const [myBalance, setMyBalance] = useState<MyBalanceResponse | null>(null);
  const [settlementPlan, setSettlementPlan] = useState<SettlementPlan | null>(null);
  const [settlements, setSettlements] = useState<SettlementItem[]>([]);
  const [invite, setInvite] = useState<CreatedInvite | null>(null);

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [groupType, setGroupType] = useState<BackendGroupType>('GENERAL');

  const [expenseTitle, setExpenseTitle] = useState('');
  const [expenseAmount, setExpenseAmount] = useState('');
  const [expenseDescription, setExpenseDescription] = useState('');
  const [expensePayerId, setExpensePayerId] = useState('');
  const [expenseParticipantIds, setExpenseParticipantIds] = useState<string[]>([]);
  const [expenseSplitMethod, setExpenseSplitMethod] = useState<ExpenseSplitMethod>('EQUAL');
  const [expenseCustomShares, setExpenseCustomShares] = useState<Record<string, string>>({});
  const [taxType, setTaxType] = useState<FeeType>('NONE');
  const [taxValue, setTaxValue] = useState('');
  const [serviceFeeType, setServiceFeeType] = useState<FeeType>('NONE');
  const [serviceFeeValue, setServiceFeeValue] = useState('');
  const [receiptFile, setReceiptFile] = useState<File | null>(null);
  const [openingReceiptId, setOpeningReceiptId] = useState<string | null>(null);

  const [manualReceiverId, setManualReceiverId] = useState('');
  const [manualAmount, setManualAmount] = useState('');
  const [manualDescription, setManualDescription] = useState('');
  const [manualPaymentMode, setManualPaymentMode] = useState<ManualPaymentMode>('FULL');
  const [selectedManualPlanItemId, setSelectedManualPlanItemId] = useState('');

  const [loading, setLoading] = useState(true);
  const [membersLoading, setMembersLoading] = useState(true);
  const [expensesLoading, setExpensesLoading] = useState(true);
  const [settlementLoading, setSettlementLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [expenseSaving, setExpenseSaving] = useState(false);
  const [settlementSaving, setSettlementSaving] = useState(false);
  const [archiveLoading, setArchiveLoading] = useState(false);
  const [leaveLoading, setLeaveLoading] = useState(false);
  const [inviteLoading, setInviteLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [autoSettlementTried, setAutoSettlementTried] = useState(false);

  const inviteUrl = useMemo(() => (invite ? getInviteUrl(invite) : ''), [invite]);

  const currentUserId = getCurrentUserId(currentUser);
  const isArchived = group?.status === 'ARCHIVED';
  const isOwner = group?.my_role === 'OWNER';
  const canManageGroup = ['OWNER', 'ADMIN'].includes(group?.my_role || '');

  const activeExpenses = useMemo(
    () => expenses.filter((expense) => expense.status !== 'DELETED' && expense.status !== 'CANCELLED'),
    [expenses],
  );

  const recentExpenses = useMemo(() => {
    return [...activeExpenses].sort((a, b) => {
      const left = new Date(a.expense_date || a.created_at || 0).getTime();
      const right = new Date(b.expense_date || b.created_at || 0).getTime();
      return right - left;
    });
  }, [activeExpenses]);

  const openPlanItems = settlementPlan?.items?.filter((item) => isOpenSettlementStatus(item.status)) || [];
  const myDebtItems = openPlanItems.filter((item) => item.payer_user_id === currentUserId);
  const myCreditItems = openPlanItems.filter((item) => item.receiver_user_id === currentUserId);

  const totalMyDebtMinor = myDebtItems.reduce((sum, item) => sum + (item.amount_minor || 0), 0);
  const totalMyCreditMinor = myCreditItems.reduce((sum, item) => sum + (item.amount_minor || 0), 0);

  const manualPayOptions = openPlanItems.filter(
    (item) => item.payer_user_id === currentUserId && ['PENDING', 'REJECTED'].includes(item.status || 'PENDING'),
  );

  const totalExpenseMinor = activeExpenses.reduce((sum, expense) => sum + getExpenseTotal(expense), 0);
  const optimizedSettlements = useMemo(
    () => calculateOptimizedSettlements(balances, members),
    [balances, members],
  );
  const currentUserOptimizedPayment = optimizedSettlements.find(
    (item) => item.payer_user_id === currentUserId,
  );
  const currentUserBalance = balances.find((balance) => balance.user_id === currentUserId);
  const myNetMinor = currentUserBalance?.net_balance_minor ?? myBalance?.net_balance_minor ?? 0;
  const myAccount = getMyAccountStatus(myNetMinor);

  const optimizedTotalDebtMinor = optimizedSettlements.reduce(
    (sum, item) => sum + (item.amount_minor || 0),
    0,
  );
  const totalOpenDebtMinor = optimizedTotalDebtMinor;
  const remainingPaymentCount = optimizedSettlements.length;
  const backendPaymentCount = openPlanItems.length;
  const currentSuggestedPayment = currentUserOptimizedPayment || null;

  const selectedManualPlanItem = manualPayOptions.find((item) => item.id === selectedManualPlanItemId) || null;

  const accountTitle = myNetMinor < 0 ? 'بدهکار هستی' : myNetMinor > 0 ? 'طلبکار هستی' : 'حسابت صاف است';
  const accountTone = myNetMinor < 0 ? 'rose' : myNetMinor > 0 ? 'emerald' : 'slate';

  const baseAmountMinor = parseAmountToMinor(expenseAmount);

  const taxAmountMinor = useMemo(() => {
    if (taxType === 'FIXED') return parseAmountToMinor(taxValue);
    if (taxType === 'PERCENTAGE') return Math.round((baseAmountMinor * parsePercentage(taxValue)) / 100);
    return 0;
  }, [baseAmountMinor, taxType, taxValue]);

  const serviceFeeAmountMinor = useMemo(() => {
    if (serviceFeeType === 'FIXED') return parseAmountToMinor(serviceFeeValue);
    if (serviceFeeType === 'PERCENTAGE') return Math.round((baseAmountMinor * parsePercentage(serviceFeeValue)) / 100);
    return 0;
  }, [baseAmountMinor, serviceFeeType, serviceFeeValue]);

  const expenseFinalTotalMinor = baseAmountMinor + taxAmountMinor + serviceFeeAmountMinor;

  const customSharesTotalMinor = expenseParticipantIds.reduce((sum, userId) => {
    return sum + parseAmountToMinor(expenseCustomShares[userId] || '');
  }, 0);

  async function loadGroup() {
    try {
      setLoading(true);
      const backendGroup = await getGroupDetail(groupId);

      setGroup(backendGroup);
      setTitle(backendGroup.title || '');
      setDescription(backendGroup.description || '');
      setGroupType(backendGroup.group_type || 'GENERAL');
      onGroupUpdated(backendGroup);
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'دریافت گروه ناموفق بود',
        description: getBackendMessage(err),
      });
    } finally {
      setLoading(false);
    }
  }

  async function loadMembers() {
    try {
      setMembersLoading(true);

      const [backendMembers, me] = await Promise.all([
        getGroupMembers(groupId),
        getCurrentUser().catch(() => null),
      ]);

      setCurrentUser(me);

      const currentUserName =
        me?.art_name ||
        me?.display_name ||
        me?.username ||
        [me?.first_name, me?.last_name].filter(Boolean).join(' ').trim() ||
        me?.phone_number ||
        me?.phone ||
        '';

      const normalizedMembers = backendMembers.map((member) => {
        const isCurrentUser = Boolean(me?.id) && getMemberUserId(member) === String(me?.id);
        if (!isCurrentUser || !currentUserName) return member;
        return { ...member, display_name: currentUserName };
      });

      setMembers(normalizedMembers);

      const ids = normalizedMembers.map(getMemberUserId).filter(Boolean);
      setExpenseParticipantIds(ids);
      setExpensePayerId(me?.id ? String(me.id) : ids[0] || '');
      setManualReceiverId(ids.find((id) => id !== String(me?.id || '')) || '');
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'دریافت اعضا ناموفق بود',
        description: getBackendMessage(err),
      });
    } finally {
      setMembersLoading(false);
    }
  }

  async function loadExpenses() {
    try {
      setExpensesLoading(true);
      const backendExpenses = await listGroupExpenses(groupId, { page_size: 100 });
      setExpenses(backendExpenses);
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'دریافت هزینه‌ها ناموفق بود',
        description: getBackendMessage(err),
      });
    } finally {
      setExpensesLoading(false);
    }
  }

  async function loadSettlementData() {
    try {
      setSettlementLoading(true);

      const [balancesResult, myBalanceResult, planResult, settlementsResult] = await Promise.allSettled([
        getGroupBalances(groupId),
        getMyGroupBalance(groupId),
        getSettlementPlan(groupId),
        listGroupSettlements(groupId),
      ]);

      setBalances(balancesResult.status === 'fulfilled' ? balancesResult.value.balances || [] : []);
      setMyBalance(myBalanceResult.status === 'fulfilled' ? myBalanceResult.value : null);
      setSettlementPlan(planResult.status === 'fulfilled' ? planResult.value : null);
      setSettlements(settlementsResult.status === 'fulfilled' ? settlementsResult.value || [] : []);
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'دریافت تسویه‌ها ناموفق بود',
        description: getBackendMessage(err),
      });
    } finally {
      setSettlementLoading(false);
    }
  }

  async function reloadAll() {
    await Promise.all([loadGroup(), loadMembers(), loadExpenses(), loadSettlementData()]);
  }

  useEffect(() => {
    void reloadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groupId]);

  async function refreshSmartSettlement(showNotification = true) {
    try {
      setSettlementSaving(true);
      const generatedPlan = await generateSettlementPlan(groupId);

      if (generatedPlan?.id && generatedPlan.status === 'DRAFT') {
        try {
          await activateSettlementPlan(generatedPlan.id);
          const latestPlan = await getSettlementPlan(groupId).catch(() => ({
            ...generatedPlan,
            status: 'ACTIVE',
          }));
          setSettlementPlan(latestPlan);
        } catch {
          setSettlementPlan(generatedPlan);
        }
      } else {
        setSettlementPlan(generatedPlan);
      }

      await loadSettlementData();

      if (showNotification) {
        notify({
          type: 'success',
          title: 'تسویه هوشمند بروزرسانی شد',
          description: 'کمترین پرداخت‌های لازم دوباره حساب شد و پیشنهادهای جدید نمایش داده شد.',
        });
      }
    } catch (err) {
      console.error(err);
      if (showNotification) {
        notify({
          type: 'error',
          title: getSettlementErrorTitle('plan'),
          description: getSettlementErrorDescription(err),
        });
      }
    } finally {
      setSettlementSaving(false);
    }
  }

  useEffect(() => {
    if (
      autoSettlementTried ||
      settlementLoading ||
      expensesLoading ||
      settlementPlan ||
      activeExpenses.length === 0 ||
      isArchived
    ) {
      return;
    }

    setAutoSettlementTried(true);
    void refreshSmartSettlement(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoSettlementTried, settlementLoading, expensesLoading, settlementPlan, activeExpenses.length, isArchived]);

  function selectManualPlanItem(item: SettlementPlanItem) {
    setSelectedManualPlanItemId(item.id);
    setManualReceiverId(item.receiver_user_id);
    setManualPaymentMode('FULL');
    setManualAmount(String(item.amount_minor));
    setManualDescription('');
  }

  function openManualPaymentForItem(item: SettlementPlanItem) {
    selectManualPlanItem(item);
    setModal('settlement');
  }

  function resetManualPaymentForm() {
    const firstOtherMember = members.find((member) => getMemberUserId(member) !== currentUserId);

    setSelectedManualPlanItemId('');
    setManualPaymentMode('FULL');
    setManualAmount('');
    setManualDescription('');
    setManualReceiverId(firstOtherMember ? getMemberUserId(firstOtherMember) : '');
  }

  async function handleSave() {
    if (!title.trim()) {
      notify({
        type: 'error',
        title: 'عنوان لازم است',
        description: 'برای گروه یک عنوان وارد کن.',
      });
      return;
    }

    try {
      setSaving(true);

      const updatedGroup = await updateGroup(groupId, {
        title: title.trim(),
        description: description.trim(),
        group_type: groupType,
      });

      setGroup(updatedGroup);
      onGroupUpdated(updatedGroup);
      setModal(null);

      notify({
        type: 'success',
        title: 'ذخیره شد',
        description: 'اطلاعات گروه بروزرسانی شد.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'ذخیره ناموفق بود',
        description: getBackendMessage(err),
      });
    } finally {
      setSaving(false);
    }
  }

  async function handleArchive() {
    const confirmed = await confirm({
      title: 'آرشیو گروه؟',
      description: 'گروه از لیست فعال‌ها خارج می‌شود.',
      confirmText: 'آرشیو کن',
      cancelText: 'انصراف',
      tone: 'warning',
    });

    if (!confirmed) return;

    try {
      setArchiveLoading(true);
      await archiveGroup(groupId);
      const refreshedGroup = await getGroupDetail(groupId);

      setGroup(refreshedGroup);
      onGroupUpdated(refreshedGroup);

      notify({
        type: 'success',
        title: 'گروه آرشیو شد',
        description: 'گروه دیگر در لیست فعال‌ها نیست.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'آرشیو ناموفق بود',
        description: getBackendMessage(err),
      });
    } finally {
      setArchiveLoading(false);
    }
  }

  async function handleRestore() {
    const confirmed = await confirm({
      title: 'فعال‌سازی گروه؟',
      description: 'گروه دوباره به لیست فعال‌ها برمی‌گردد.',
      confirmText: 'فعال کن',
      cancelText: 'انصراف',
      tone: 'success',
    });

    if (!confirmed) return;

    try {
      setArchiveLoading(true);
      const restoredGroup = await restoreGroup(groupId);

      setGroup(restoredGroup);
      onGroupUpdated(restoredGroup);

      notify({
        type: 'success',
        title: 'گروه فعال شد',
        description: 'گروه دوباره قابل استفاده است.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'فعال‌سازی ناموفق بود',
        description: getBackendMessage(err),
      });
    } finally {
      setArchiveLoading(false);
    }
  }

  async function handleLeave() {
    if (isOwner) {
      notify({
        type: 'info',
        title: 'مالک نمی‌تواند خارج شود',
        description: 'مالکیت را منتقل کن یا گروه را آرشیو کن.',
      });
      return;
    }

    const confirmed = await confirm({
      title: 'خروج از گروه؟',
      description: 'این گروه از لیست تو حذف می‌شود.',
      confirmText: 'خارج شو',
      cancelText: 'انصراف',
      tone: 'danger',
    });

    if (!confirmed) return;

    try {
      setLeaveLoading(true);
      await leaveGroup(groupId);

      notify({
        type: 'success',
        title: 'خارج شدی',
        description: 'گروه از لیست تو حذف شد.',
      });

      onGroupRemoved(groupId);
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'خروج ناموفق بود',
        description: getBackendMessage(err),
      });
    } finally {
      setLeaveLoading(false);
    }
  }

  async function handleRemoveMember(member: BackendGroupMember) {
    const memberId = getMemberId(member);

    if (!memberId) {
      notify({
        type: 'error',
        title: 'حذف عضو انجام نشد',
        description: 'اطلاعات عضو کامل نیست.',
      });
      return;
    }

    const confirmed = await confirm({
      title: 'حذف عضو؟',
      description: `${getMemberName(member)} از گروه حذف شود؟`,
      confirmText: 'حذف کن',
      cancelText: 'انصراف',
      tone: 'danger',
    });

    if (!confirmed) return;

    try {
      await removeGroupMember(groupId, memberId);
      setMembers((prev) => prev.filter((item) => getMemberId(item) !== memberId));

      notify({
        type: 'success',
        title: 'عضو حذف شد',
        description: 'لیست اعضا بروزرسانی شد.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'حذف عضو ناموفق بود',
        description: getBackendMessage(err),
      });
    }
  }

  function toggleExpenseParticipant(userId: string) {
    setExpenseParticipantIds((prev) =>
      prev.includes(userId) ? prev.filter((item) => item !== userId) : [...prev, userId],
    );
  }

  function resetExpenseForm() {
    setExpenseTitle('');
    setExpenseAmount('');
    setExpenseDescription('');
    setReceiptFile(null);
    setTaxType('NONE');
    setTaxValue('');
    setServiceFeeType('NONE');
    setServiceFeeValue('');
    setExpenseSplitMethod('EQUAL');
    setExpenseCustomShares({});
    setShowAdvancedExpense(false);
  }

  async function handleCreateExpense() {
    if (isArchived) {
      notify({
        type: 'error',
        title: 'گروه آرشیو شده',
        description: 'برای ثبت هزینه، اول گروه را فعال کن.',
      });
      return;
    }

    if (!expenseTitle.trim()) {
      notify({
        type: 'error',
        title: 'عنوان هزینه لازم است',
        description: 'مثلاً شام، تاکسی یا خرید.',
      });
      return;
    }

    if (!baseAmountMinor || baseAmountMinor <= 0) {
      notify({
        type: 'error',
        title: 'مبلغ درست نیست',
        description: 'مبلغ هزینه را وارد کن.',
      });
      return;
    }

    if (!expensePayerId) {
      notify({
        type: 'error',
        title: 'پرداخت‌کننده مشخص نیست',
        description: 'یک نفر را به عنوان پرداخت‌کننده انتخاب کن.',
      });
      return;
    }

    if (expenseParticipantIds.length === 0) {
      notify({
        type: 'error',
        title: 'اعضا مشخص نیستند',
        description: 'حداقل یک عضو را انتخاب کن.',
      });
      return;
    }

    const customParticipants = expenseParticipantIds.map((userId) => ({
      user_id: userId,
      base_share_minor: parseAmountToMinor(expenseCustomShares[userId] || ''),
    }));

    if (expenseSplitMethod === 'CUSTOM_AMOUNT') {
      const hasInvalidShare = customParticipants.some((participant) => participant.base_share_minor <= 0);

      if (hasInvalidShare) {
        notify({
          type: 'error',
          title: 'سهم‌ها کامل نیستند',
          description: 'برای همه اعضای انتخاب‌شده سهم وارد کن.',
        });
        return;
      }

      if (customSharesTotalMinor !== baseAmountMinor) {
        notify({
          type: 'error',
          title: 'جمع سهم‌ها درست نیست',
          description: `جمع سهم‌ها باید ${formatMoney(baseAmountMinor)} باشد.`,
        });
        return;
      }
    }

    try {
      setExpenseSaving(true);

      let receiptFileId: string | undefined;

      if (receiptFile) {
        const uploadedReceipt = await uploadReceipt({ groupId, file: receiptFile });
        receiptFileId = uploadedReceipt.id;
      }

      await createGroupExpense(groupId, {
        title: expenseTitle.trim(),
        description: expenseDescription.trim(),
        payer_user_id: expensePayerId,
        base_amount_minor: baseAmountMinor,
        currency: 'IRR',
        split_method: expenseSplitMethod,
        participant_user_ids: expenseSplitMethod === 'EQUAL' ? expenseParticipantIds : undefined,
        participants: expenseSplitMethod === 'CUSTOM_AMOUNT' ? customParticipants : undefined,
        tax_type: taxType,
        tax_percentage: taxType === 'PERCENTAGE' ? String(parsePercentage(taxValue)) : undefined,
        tax_amount_minor: taxType === 'FIXED' ? taxAmountMinor : undefined,
        service_fee_type: serviceFeeType,
        service_fee_percentage: serviceFeeType === 'PERCENTAGE' ? String(parsePercentage(serviceFeeValue)) : undefined,
        service_fee_amount_minor: serviceFeeType === 'FIXED' ? serviceFeeAmountMinor : undefined,
        receipt_file_id: receiptFileId,
      });

      resetExpenseForm();
      setModal(null);
      await Promise.all([loadExpenses(), loadSettlementData()]);
      void refreshSmartSettlement(false);

      notify({
        type: 'success',
        title: 'هزینه ثبت شد',
        description: 'حساب گروه بروزرسانی شد.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'ثبت هزینه ناموفق بود',
        description: getBackendMessage(err),
      });
    } finally {
      setExpenseSaving(false);
    }
  }

  async function handleOpenReceipt(fileId?: string) {
    if (!fileId) return;

    try {
      setOpeningReceiptId(fileId);
      await openMediaFile(fileId);
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'رسید باز نشد',
        description: getBackendMessage(err),
      });
    } finally {
      setOpeningReceiptId(null);
    }
  }

  async function handleDeleteExpense(expense: BackendExpense) {
    const confirmed = await confirm({
      title: 'حذف هزینه؟',
      description: `هزینه «${expense.title}» حذف شود؟`,
      confirmText: 'حذف کن',
      cancelText: 'انصراف',
      tone: 'danger',
    });

    if (!confirmed) return;

    try {
      await deleteExpense(expense.id);
      await Promise.all([loadExpenses(), loadSettlementData()]);
      void refreshSmartSettlement(false);

      notify({
        type: 'success',
        title: 'هزینه حذف شد',
        description: 'حساب گروه بروزرسانی شد.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'حذف هزینه ناموفق بود',
        description: getBackendMessage(err),
      });
    }
  }

  async function handleCreateManualSettlement(receiverUserId?: string, amountMinor?: number) {
    const selectedItem = selectedManualPlanItem;
    const isSelectedFullPayment = selectedItem && manualPaymentMode === 'FULL';
    const targetReceiverId = selectedItem?.receiver_user_id || receiverUserId || manualReceiverId;
    const targetAmountMinor = selectedItem
      ? manualPaymentMode === 'FULL'
        ? selectedItem.amount_minor
        : parseAmountToMinor(manualAmount)
      : amountMinor ?? parseAmountToMinor(manualAmount);
    const targetSuggestion = optimizedSettlements.find(
      (item) => item.receiver_user_id === targetReceiverId && item.payer_user_id === currentUserId,
    );

    if (isArchived) {
      notify({
        type: 'error',
        title: 'گروه آرشیو شده',
        description: 'برای ثبت پرداخت، اول گروه را فعال کن.',
      });
      return;
    }

    if (!currentUserId) {
      notify({
        type: 'error',
        title: 'کاربر مشخص نیست',
        description: 'یک بار از حساب خارج شو و دوباره وارد شو تا پرداخت به نام خودت ثبت شود.',
      });
      return;
    }

    if (!targetReceiverId) {
      notify({
        type: 'error',
        title: 'دریافت‌کننده مشخص نیست',
        description: 'یک پرداخت یا یک عضو را انتخاب کن.',
      });
      return;
    }

    if (!targetAmountMinor || targetAmountMinor <= 0) {
      notify({
        type: 'error',
        title: 'مبلغ درست نیست',
        description: 'مبلغ پرداخت را وارد کن.',
      });
      return;
    }

    if (selectedItem && targetAmountMinor > selectedItem.amount_minor) {
      notify({
        type: 'error',
        title: 'مبلغ زیاد است',
        description: `حداکثر مبلغ این پرداخت ${formatMoney(selectedItem.amount_minor)} است.`,
      });
      return;
    }

    if (!selectedItem && targetSuggestion && targetAmountMinor > targetSuggestion.amount_minor) {
      notify({
        type: 'info',
        title: 'مبلغ بیشتر از پیشنهاد تسویه است',
        description: `برای این عضو، مبلغ پیشنهادی ${formatMoney(targetSuggestion.amount_minor)} است. مبلغ را اصلاح کن یا از دکمه پیشنهاد استفاده کن.`,
      });
      return;
    }

    try {
      setSettlementSaving(true);

      if (isSelectedFullPayment) {
        await reportPlanItemPaid(selectedItem.id);
      } else {
        await createGroupSettlement(groupId, {
          receiver_user_id: targetReceiverId,
          amount_minor: targetAmountMinor,
          currency: 'IRR',
          description:
            manualDescription ||
            (selectedItem
              ? `پرداخت بخشی از بدهی به ${getPlanPartyName(selectedItem, 'receiver', members)}`
              : 'تسویه دستی'),
        });
      }

      setManualReceiverId('');
      setManualAmount('');
      setManualDescription('');

      resetManualPaymentForm();
      await loadSettlementData();

      notify({
        type: 'success',
        title: isSelectedFullPayment ? 'پرداخت گزارش شد' : 'پرداخت ثبت شد',
        description: isSelectedFullPayment
          ? 'در انتظار تأیید دریافت‌کننده است.'
          : 'بعد از تأیید دریافت‌کننده، مبلغ از بدهی باقی‌مانده کم می‌شود.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: getSettlementErrorTitle('create'),
        description: getSettlementErrorDescription(err),
      });
    } finally {
      setSettlementSaving(false);
    }
  }

  async function handlePlanItemAction(item: SettlementPlanItem, action: 'paid' | 'confirm' | 'reject') {
    try {
      setSettlementSaving(true);

      if (action === 'paid') await reportPlanItemPaid(item.id);
      if (action === 'confirm') await confirmPlanItem(item.id);
      if (action === 'reject') await rejectPlanItem(item.id);

      await loadSettlementData();

      if (action === 'confirm') {
        void refreshSmartSettlement(false);
      }

      notify({
        type: 'success',
        title: 'تسویه بروزرسانی شد',
        description: 'وضعیت پرداخت تغییر کرد.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: getSettlementErrorTitle('item'),
        description: getSettlementErrorDescription(err),
      });
    } finally {
      setSettlementSaving(false);
    }
  }

  async function handleSettlementAction(settlement: SettlementItem, action: 'confirm' | 'reject' | 'cancel') {
    try {
      setSettlementSaving(true);

      if (action === 'confirm') await confirmSettlement(settlement.id);
      if (action === 'reject') await rejectSettlement(settlement.id);
      if (action === 'cancel') await cancelSettlement(settlement.id);

      await loadSettlementData();

      if (action === 'confirm' || action === 'cancel') {
        void refreshSmartSettlement(false);
      }

      notify({
        type: 'success',
        title: 'پرداخت بروزرسانی شد',
        description: 'لیست پرداخت‌ها تازه شد.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: getSettlementErrorTitle('review'),
        description: getSettlementErrorDescription(err),
      });
    } finally {
      setSettlementSaving(false);
    }
  }

  async function handleCreateInvite() {
    try {
      setInviteLoading(true);

      const createdInvite = await createGroupInvite(groupId, {
        expires_in_hours: 72,
        max_uses: 10,
      });

      setInvite(createdInvite);

      notify({
        type: 'success',
        title: 'لینک ساخته شد',
        description: 'لینک دعوت آماده کپی است.',
      });
    } catch (err) {
      console.error(err);

      const permissionDenied = isApiError(err) && err.status === 403;

      notify({
        type: 'error',
        title: permissionDenied ? 'اجازه ساخت لینک نداری' : 'ساخت لینک ناموفق بود',
        description: permissionDenied ? 'فقط مدیر یا مالک می‌تواند لینک بسازد.' : getBackendMessage(err),
      });
    } finally {
      setInviteLoading(false);
    }
  }

  async function handleCopyInvite() {
    if (!inviteUrl) return;

    try {
      await navigator.clipboard.writeText(inviteUrl);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);

      notify({
        type: 'success',
        title: 'کپی شد',
        description: 'لینک دعوت کپی شد.',
      });
    } catch {
      notify({
        type: 'error',
        title: 'کپی نشد',
        description: 'لینک را دستی کپی کن.',
      });
    }
  }

  async function handleRevokeInvite() {
    if (!invite) return;

    const inviteId = getInviteId(invite);

    if (!inviteId) {
      notify({
        type: 'error',
        title: 'لغو انجام نشد',
        description: 'اطلاعات لینک کامل نیست.',
      });
      return;
    }

    const confirmed = await confirm({
      title: 'لغو لینک دعوت؟',
      description: 'این لینک دیگر قابل استفاده نخواهد بود.',
      confirmText: 'لغو کن',
      cancelText: 'انصراف',
      tone: 'danger',
    });

    if (!confirmed) return;

    try {
      await revokeGroupInvite(groupId, inviteId);
      setInvite(null);

      notify({
        type: 'success',
        title: 'لینک لغو شد',
        description: 'دعوت دیگر فعال نیست.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'لغو لینک ناموفق بود',
        description: getBackendMessage(err),
      });
    }
  }

  if (loading && !group) {
    return (
      <main className="min-h-[70vh] px-4 py-8" dir="rtl">
        <div className="dashboard-section-card mx-auto flex max-w-[1100px] items-center justify-center rounded-[24px] border border-emerald-100/80 bg-white/95 p-10 text-center shadow-[0_18px_44px_rgba(15,23,42,0.07)] backdrop-blur dark:border-emerald-500/20 dark:bg-slate-950/90">
          <InlineLoader label="در حال دریافت گروه..." />
        </div>
      </main>
    );
  }

  return (
    <main className="relative min-h-screen overflow-x-hidden px-3 pb-10 pt-3 text-right sm:px-5 xl:px-8" dir="rtl">
      <div className="mx-auto max-w-[1160px] space-y-4 sm:space-y-5">
        <header className={cn(dashboardCard, 'sticky top-3 z-40 p-3 sm:p-4')}>
          <div className="flex items-center justify-between gap-3">
            <button
              type="button"
              onClick={() => setModal('settings')}
              className="group flex min-w-0 flex-1 items-center gap-3 rounded-[20px] px-2 py-1 text-right transition hover:bg-emerald-50/60 dark:hover:bg-emerald-500/10"
            >
              <div className="dashboard-row-avatar flex h-12 w-12 shrink-0 items-center justify-center rounded-full border border-emerald-200 bg-emerald-50 text-lg font-black text-emerald-700 shadow-sm dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-200">
                {(group?.title || 'گ').slice(0, 1)}
              </div>

              <div className="min-w-0 text-right">
                <h1 className="truncate text-lg font-black tracking-[-0.03em] text-text dark:text-slate-100 sm:text-xl">
                  {group?.title || 'جزئیات گروه'}
                </h1>

                <p className="mt-0.5 text-xs font-bold text-muted dark:text-slate-400">
                  {membersLoading ? 'در حال دریافت اعضا...' : `${toPersianNumber(members.length)} عضو`}
                </p>
              </div>
            </button>

            <Button tone="secondary" onClick={onBack} className="min-h-11 px-3 sm:px-4">
              <span dir="rtl" className="inline-flex items-center gap-2">
                <span className="hidden sm:inline">بازگشت</span>
                <ArrowLeft className="h-4 w-4" />
              </span>
            </Button>
          </div>
        </header>

        <section dir="ltr" className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px] xl:items-start">
          <aside dir="rtl" className="order-1 space-y-4 xl:order-2 xl:h-[460px] xl:sticky xl:top-[104px]">
            <div
              className={cn(
                'dashboard-balance-card flex h-full flex-col overflow-hidden rounded-[28px] border p-4 text-right shadow-[0_18px_44px_rgba(15,23,42,0.08)] dark:shadow-[0_24px_58px_rgba(0,0,0,0.28)]',
                accountTone === 'rose'
                  ? 'border-rose-200 bg-gradient-to-br from-white via-rose-50/90 to-orange-50/80 dark:border-rose-500/25 dark:from-slate-950 dark:via-slate-950 dark:to-rose-950/30'
                  : accountTone === 'emerald'
                    ? 'border-emerald-200 bg-gradient-to-br from-white via-emerald-50/90 to-sky-50/70 dark:border-emerald-500/25 dark:from-slate-950 dark:via-slate-950 dark:to-emerald-950/30'
                    : 'border-slate-200 bg-gradient-to-br from-white via-slate-50/90 to-emerald-50/50 dark:border-slate-700 dark:from-slate-950 dark:via-slate-950 dark:to-slate-900',
              )}
            >
              <div className="mb-4 flex items-start justify-between gap-3">
                <div className="min-w-0 text-right">
                  <p className="text-xs font-black text-muted dark:text-slate-400">وضعیت من</p>
                  <h2
                    className={cn(
                      'mt-1 text-2xl font-black tracking-[-0.04em]',
                      accountTone === 'rose'
                        ? 'text-rose-700 dark:text-rose-200'
                        : accountTone === 'emerald'
                          ? 'text-emerald-700 dark:text-emerald-200'
                          : 'text-slate-700 dark:text-slate-200',
                    )}
                  >
                    {accountTitle}
                  </h2>
                </div>

                <div
                  className={cn(
                    'flex h-12 w-12 shrink-0 items-center justify-center rounded-[18px] text-white shadow-[0_12px_26px_rgba(15,23,42,0.12)]',
                    accountTone === 'rose'
                      ? 'bg-rose-500 dark:bg-rose-500'
                      : accountTone === 'emerald'
                        ? 'bg-emerald-600 dark:bg-emerald-500'
                        : 'bg-slate-700 dark:bg-slate-600',
                  )}
                >
                  <Banknote className="h-6 w-6" />
                </div>
              </div>

              <div className="rounded-[22px] border border-white/80 bg-white/90 p-4 text-right shadow-[0_10px_28px_rgba(15,23,42,0.055)] dark:border-slate-700/80 dark:bg-slate-900/80">
                <p className="text-xs font-extrabold text-muted dark:text-slate-400">خالص حساب تو</p>
                <div className={cn('mt-1', accountTone === 'rose' ? 'text-rose-700 dark:text-rose-200' : accountTone === 'emerald' ? 'text-emerald-700 dark:text-emerald-200' : 'text-slate-700 dark:text-slate-200')}>
                  <MoneyWithWords
                    amount={myNetMinor}
                    valueClassName="text-4xl font-black tracking-[-0.06em]"
                    textClassName="mt-1 text-[10px] font-semibold opacity-70"
                    showText={true}
                  />
                </div>
              </div>

              <div className="mt-3 grid grid-cols-2 gap-2">
                <MiniNumberCard label="پرداخت کنی" value={totalMyDebtMinor} tone="rose" />
                <MiniNumberCard label="دریافت کنی" value={totalMyCreditMinor} tone="emerald" />
              </div>

              <div className="mt-auto grid gap-2 pt-4">
                <Button onClick={() => setModal('expense')} disabled={isArchived} className="h-12 w-full text-base">
                  <Plus className="h-5 w-5" />
                  ثبت هزینه
                </Button>

                <Button tone="secondary" onClick={() => setModal('settlement')} className="h-12 w-full">
                  <HandCoins className="h-5 w-5" />
                  جزئیات تسویه
                </Button>
              </div>
            </div>
          </aside>

          <div dir="rtl" className="order-2 space-y-4 xl:order-1 xl:h-[460px]">
            <section
              className={cn(
                dashboardCard,
                'flex h-full min-h-[360px] max-h-[560px] flex-col overflow-hidden p-4 sm:p-5 xl:max-h-[460px]',
              )}
            >
              <SectionHeader
                title="تسویه هوشمند من"
                action={
                  <Button
                    tone="secondary"
                    onClick={() => void refreshSmartSettlement()}
                    disabled={settlementSaving || isArchived}
                    className="min-h-10 px-3 text-xs"
                  >
                    {settlementSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                    محاسبه
                  </Button>
                }
              />

              <div className={cn(scrollAreaClass, 'flex-1')}>
                {settlementLoading ? (
                  <div className="dashboard-panel-state flex min-h-[260px] items-center justify-center gap-2 rounded-[20px] border border-dashed border-emerald-200 bg-white/[0.65] p-6 text-sm font-bold text-muted dark:border-emerald-500/20 dark:bg-slate-900/70 dark:text-slate-400">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    در حال دریافت تسویه...
                  </div>
                ) : myDebtItems.length === 0 && myCreditItems.length === 0 ? (
                  <EmptyState
                    title="تسویه‌ای برای تو نیست"
                    description="اگر هزینه‌ای ثبت شده، محاسبه را بزن."
                    icon={<Check className="h-6 w-6" />}
                  />
                ) : (
                  <div className="grid gap-4 lg:grid-cols-2">
                    <div className="dashboard-section-card dashboard-section-card--quiet rounded-[24px] border border-rose-200 bg-rose-50/55 p-4 text-right dark:border-rose-500/25 dark:bg-rose-500/10">
                      <div className="mb-3 flex items-center justify-between gap-3">
                        <h3 className="text-base font-black text-rose-700 dark:text-rose-200">پرداخت‌های تو</h3>
                        <span className="rounded-[16px] bg-rose-600 px-3 py-1.5 text-xs font-black text-white dark:bg-rose-500 dark:text-white">
                          {formatMoney(totalMyDebtMinor)}
                        </span>
                      </div>

                      {myDebtItems.length === 0 ? (
                        <div className="rounded-[20px] border border-dashed border-rose-200 bg-white/70 p-4 text-center text-xs font-bold text-muted dark:border-rose-500/25 dark:bg-slate-900/60 dark:text-slate-400">
                          لازم نیست پولی پرداخت کنی.
                        </div>
                      ) : (
                        <div className={cn(scrollAreaClass, 'max-h-[260px] space-y-2 pr-0.5')}>
                          {myDebtItems.map((item) => (
                            <div
                              key={item.id}
                              className="dashboard-list-row dashboard-list-card rounded-[20px] border border-rose-200 bg-white/95 p-3 text-right shadow-[0_8px_20px_rgba(15,23,42,0.035)] dark:border-rose-500/20 dark:bg-slate-900/80"
                            >
                              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                                <div className="min-w-0 text-right">
                                  <p className="text-sm font-black text-text dark:text-slate-100">
                                    به {getPlanPartyName(item, 'receiver', members)}
                                  </p>
                                  <p className="mt-1 text-xs font-bold text-muted dark:text-slate-400">
                                    {getSettlementStatusLabel(item.status)}
                                  </p>
                                </div>

                                <div className="flex flex-wrap items-center justify-start gap-2">
                                  <MoneyWithWords
                                    amount={item.amount_minor}
                                    className="rounded-[16px] bg-rose-50 px-3 py-2 text-sm font-black text-rose-700 dark:bg-rose-500/10 dark:text-rose-200"
                                    valueClassName="text-sm font-black"
                                    textClassName="mt-1 text-[10px] font-semibold text-rose-700/70 dark:text-rose-200/70"
                                    showText={true}
                                  />

                                  {canReportPlanItem(item, settlementPlan) ? (
                                    <Button
                                      onClick={() => openManualPaymentForItem(item)}
                                      className="min-h-10 px-3 text-xs"
                                    >
                                      پرداخت
                                    </Button>
                                  ) : null}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="dashboard-section-card dashboard-section-card--quiet rounded-[24px] border border-emerald-200 bg-emerald-50/60 p-4 text-right dark:border-emerald-500/25 dark:bg-emerald-500/10">
                      <div className="mb-3 flex items-center justify-between gap-3">
                        <h3 className="text-base font-black text-emerald-700 dark:text-emerald-200">دریافت‌های تو</h3>
                        <span className="rounded-[16px] bg-emerald-600 px-3 py-1.5 text-xs font-black text-white dark:bg-emerald-500 dark:text-white">
                          {formatMoney(totalMyCreditMinor)}
                        </span>
                      </div>

                      {myCreditItems.length === 0 ? (
                        <div className="rounded-[20px] border border-dashed border-emerald-200 bg-white/70 p-4 text-center text-xs font-bold text-muted dark:border-emerald-500/25 dark:bg-slate-900/60 dark:text-slate-400">
                          کسی به تو بدهکار نیست.
                        </div>
                      ) : (
                        <div className={cn(scrollAreaClass, 'max-h-[260px] space-y-2 pr-0.5')}>
                          {myCreditItems.map((item) => (
                            <div
                              key={item.id}
                              className="dashboard-list-row dashboard-list-card rounded-[20px] border border-emerald-200 bg-white/95 p-3 text-right shadow-[0_8px_20px_rgba(15,23,42,0.035)] dark:border-emerald-500/20 dark:bg-slate-900/80"
                            >
                              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                                <div className="min-w-0 text-right">
                                  <p className="text-sm font-black text-text dark:text-slate-100">
                                    از {getPlanPartyName(item, 'payer', members)}
                                  </p>
                                  <p className="mt-1 text-xs font-bold text-muted dark:text-slate-400">
                                    {getSettlementStatusLabel(item.status)}
                                  </p>
                                </div>

                                <div className="flex flex-wrap items-center justify-start gap-2">
                                  <MoneyWithWords
                                    amount={item.amount_minor}
                                    className="rounded-[16px] bg-emerald-50 px-3 py-2 text-sm font-black text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-200"
                                    valueClassName="text-sm font-black"
                                    textClassName="mt-1 text-[10px] font-semibold text-emerald-700/70 dark:text-emerald-200/70"
                                    showText={true}
                                  />

                                  {canReviewPlanItem(item) ? (
                                    <>
                                      <Button
                                        onClick={() => void handlePlanItemAction(item, 'confirm')}
                                        disabled={settlementSaving}
                                        className="min-h-10 px-3 text-xs"
                                      >
                                        گرفتم
                                      </Button>

                                      <Button
                                        tone="danger"
                                        onClick={() => void handlePlanItemAction(item, 'reject')}
                                        disabled={settlementSaving}
                                        className="min-h-10 px-3 text-xs"
                                      >
                                        نگرفتم
                                      </Button>
                                    </>
                                  ) : null}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </section>
          </div>

          <section
            dir="rtl"
            className={cn(dashboardCard, 'order-3 flex max-h-[470px] flex-col overflow-hidden p-4 sm:p-5 xl:col-span-2')}
          >
            <SectionHeader
              title="هزینه‌های اخیر"
              action={
                <button
                  type="button"
                  onClick={() => setModal('activity')}
                  className="dashboard-section-action inline-flex min-h-10 items-center justify-center gap-2 rounded-[18px] border border-emerald-200 bg-emerald-50/80 px-3 text-xs font-black text-emerald-700 transition hover:bg-emerald-100 dark:border-emerald-500/25 dark:bg-emerald-500/10 dark:text-emerald-200 dark:hover:bg-emerald-500/15"
                >
                  همه هزینه‌ها
                  <ArrowLeft className="h-4 w-4" />
                </button>
              }
            />

            <div className={cn(scrollAreaClass, 'flex-1')}>
              {expensesLoading ? (
                <div className="dashboard-panel-state flex items-center justify-center gap-2 rounded-[20px] border border-dashed border-emerald-200 bg-white/[0.65] p-6 text-sm font-bold text-muted dark:border-emerald-500/20 dark:bg-slate-900/70 dark:text-slate-400">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  در حال دریافت...
                </div>
              ) : recentExpenses.length === 0 ? (
                <EmptyState
                  title="هزینه‌ای ثبت نشده"
                  description="اولین هزینه را ثبت کن."
                  icon={<ReceiptText className="h-6 w-6" />}
                />
              ) : (
                <div className="grid gap-2 lg:grid-cols-2">
                  {recentExpenses.slice(0, 8).map((expense) => (
                    <div key={expense.id} className={cn(dashboardRow, 'px-4 py-4 sm:px-5')}>
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <div className="min-w-0 text-right">
                          <p className="truncate text-sm font-black text-text dark:text-slate-100">{expense.title}</p>
                          <MetaTags
                            user={getUserDisplayFromId(expense.payer_user_id, members)}
                            date={toPersianDate(expense.expense_date || expense.created_at)}
                          />
                        </div>

                        <div className="shrink-0 text-right">
                          <p className="rounded-[16px] bg-emerald-50 px-3 py-2 text-sm font-black text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-200">
                            {formatMoney(getExpenseTotal(expense))}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>
        </section>
      </div>

      <Modal
        open={modal === 'expense'}
        onClose={() => setModal(null)}
        title="ثبت هزینه"
        icon={<ReceiptText className="h-5 w-5" />}
        size="lg"
      >
        <div className="space-y-4 text-right">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="عنوان">
              <input
                dir="rtl"
                value={expenseTitle}
                onChange={(event) => setExpenseTitle(event.target.value)}
                placeholder="مثلاً شام"
                className={inputClass}
              />
            </Field>

            <Field label="مبلغ">
              <input
                dir="rtl"
                value={expenseAmount}
                onChange={(event) => setExpenseAmount(event.target.value)}
                placeholder="مثلاً ۲۵۰٬۰۰۰"
                inputMode="numeric"
                className={inputClass}
              />
            </Field>
          </div>

          <Field label="پرداخت‌کننده">
            <select
              value={expensePayerId}
              onChange={(event) => setExpensePayerId(event.target.value)}
              className={inputClass}
            >
              {members.map((member) => {
                const userId = getMemberUserId(member);
                return (
                  <option key={userId} value={userId}>
                    {getMemberName(member)}
                  </option>
                );
              })}
            </select>
          </Field>

          <div className={cn(dashboardQuietCard, 'flex max-h-[420px] flex-col overflow-hidden p-4 text-right')}>
            <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
              <h3 className="text-sm font-black text-text dark:text-slate-100">تقسیم بین اعضا</h3>

              <div className="flex rounded-[18px] bg-white p-1 shadow-[0_8px_20px_rgba(15,23,42,0.035)] dark:bg-slate-900">
                <button
                  type="button"
                  onClick={() => setExpenseSplitMethod('EQUAL')}
                  className={cn(
                    'rounded-[18px] px-3 py-2 text-xs font-black transition',
                    expenseSplitMethod === 'EQUAL'
                      ? 'bg-emerald-600 text-white dark:bg-emerald-500'
                      : 'text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800',
                  )}
                >
                  مساوی
                </button>

                <button
                  type="button"
                  onClick={() => setExpenseSplitMethod('CUSTOM_AMOUNT')}
                  className={cn(
                    'rounded-[18px] px-3 py-2 text-xs font-black transition',
                    expenseSplitMethod === 'CUSTOM_AMOUNT'
                      ? 'bg-emerald-600 text-white dark:bg-emerald-500'
                      : 'text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800',
                  )}
                >
                  متفاوت
                </button>
              </div>
            </div>

            <div className={cn(scrollAreaClass, 'flex-1')}>
              <div className="grid gap-2 sm:grid-cols-2">
                {members.map((member) => {
                  const userId = getMemberUserId(member);
                  const selected = expenseParticipantIds.includes(userId);

                  return (
                    <div
                      key={userId}
                      className={cn(
                        'dashboard-list-card rounded-[20px] border bg-white/92 p-3 text-right shadow-[0_8px_22px_rgba(15,23,42,0.035)] transition dark:bg-slate-900/80',
                        selected
                          ? 'border-emerald-300/80 dark:border-emerald-500/30'
                          : 'border-emerald-200/70 opacity-70 dark:border-slate-700',
                      )}
                    >
                      <button
                        type="button"
                        onClick={() => toggleExpenseParticipant(userId)}
                        className="flex w-full items-center justify-between gap-3 text-right"
                      >
                        <div className="flex min-w-0 items-center gap-3 text-right">
                          <MemberAvatar name={getMemberName(member)} owner={member.role === 'OWNER'} />
                          <span className="truncate text-sm font-black text-text dark:text-slate-100">{getMemberName(member)}</span>
                        </div>

                        <span
                          className={cn(
                            'flex h-8 w-8 items-center justify-center rounded-[18px]',
                            selected
                              ? 'bg-emerald-600 text-white dark:bg-emerald-500'
                              : 'bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500',
                          )}
                        >
                          {selected ? <Check className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
                        </span>
                      </button>

                      {expenseSplitMethod === 'CUSTOM_AMOUNT' && selected ? (
                        <input
                          dir="rtl"
                          inputMode="numeric"
                          value={expenseCustomShares[userId] || ''}
                          onChange={(event) => setExpenseCustomShares((prev) => ({ ...prev, [userId]: event.target.value }))}
                          placeholder="سهم این نفر"
                          className="mt-3 h-10 w-full rounded-[18px] border border-emerald-200/90 bg-slate-50 px-3 text-right text-xs font-bold outline-none focus:border-emerald-400 focus:bg-white dark:border-emerald-500/20 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-500 dark:focus:bg-slate-950"
                        />
                      ) : null}
                    </div>
                  );
                })}
              </div>

              {expenseSplitMethod === 'CUSTOM_AMOUNT' ? (
                <p className="mt-3 rounded-[18px] border border-emerald-200/70 bg-white px-3 py-2 text-right text-xs font-black text-slate-600 shadow-[0_8px_20px_rgba(15,23,42,0.035)] dark:border-emerald-500/20 dark:bg-slate-900 dark:text-slate-300">
                  جمع سهم‌ها: {formatMoney(customSharesTotalMinor)} از {formatMoney(baseAmountMinor)}
                </p>
              ) : null}
            </div>
          </div>

          <button
            type="button"
            onClick={() => setShowAdvancedExpense((prev) => !prev)}
            className="flex w-full items-center justify-between rounded-[18px] border border-emerald-200/80 bg-white px-4 py-3 text-right text-sm font-black text-slate-700 shadow-[0_10px_26px_rgba(15,23,42,0.04)] transition hover:bg-emerald-50/40 dark:border-emerald-500/20 dark:bg-slate-900/80 dark:text-slate-200 dark:hover:bg-emerald-500/10"
          >
            گزینه‌های بیشتر
            <Plus className={cn('h-4 w-4 transition', showAdvancedExpense && 'rotate-45')} />
          </button>

          {showAdvancedExpense ? (
            <div className={cn(dashboardQuietCard, 'max-h-[360px] overflow-y-auto space-y-3 p-4 text-right')}>
              <Field label="توضیح">
                <textarea
                  dir="rtl"
                  value={expenseDescription}
                  onChange={(event) => setExpenseDescription(event.target.value)}
                  placeholder="اختیاری"
                  className={textareaClass}
                />
              </Field>

              <Field label="رسید">
                <div className="flex min-h-12 items-center rounded-[18px] border border-emerald-200/90 bg-white px-3 py-2 text-right dark:border-emerald-500/20 dark:bg-slate-900/80">
                  <Upload className="ml-2 h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-300" />
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/jpg,image/webp,application/pdf"
                    onChange={(event) => setReceiptFile(event.target.files?.[0] || null)}
                    className="w-full text-right text-xs font-bold text-slate-600 file:ml-3 file:rounded-[18px] file:border-0 file:bg-emerald-50 file:px-3 file:py-2 file:text-xs file:font-black file:text-emerald-700 dark:text-slate-300 dark:file:bg-emerald-500/10 dark:file:text-emerald-200"
                  />
                </div>
              </Field>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="grid grid-cols-[135px_1fr] gap-2">
                  <select
                    value={taxType}
                    onChange={(event) => setTaxType(event.target.value as FeeType)}
                    className={inputClass}
                  >
                    <option value="NONE">بدون مالیات</option>
                    <option value="PERCENTAGE">درصد مالیات</option>
                    <option value="FIXED">مبلغ مالیات</option>
                  </select>

                  <input
                    dir="rtl"
                    value={taxValue}
                    onChange={(event) => setTaxValue(event.target.value)}
                    disabled={taxType === 'NONE'}
                    placeholder="مقدار"
                    className={inputClass}
                  />
                </div>

                <div className="grid grid-cols-[135px_1fr] gap-2">
                  <select
                    value={serviceFeeType}
                    onChange={(event) => setServiceFeeType(event.target.value as FeeType)}
                    className={inputClass}
                  >
                    <option value="NONE">بدون خدمات</option>
                    <option value="PERCENTAGE">درصد خدمات</option>
                    <option value="FIXED">مبلغ خدمات</option>
                  </select>

                  <input
                    dir="rtl"
                    value={serviceFeeValue}
                    onChange={(event) => setServiceFeeValue(event.target.value)}
                    disabled={serviceFeeType === 'NONE'}
                    placeholder="مقدار"
                    className={inputClass}
                  />
                </div>
              </div>
            </div>
          ) : null}

          <div className="dashboard-balance-mini dashboard-balance-mini--credit rounded-[22px] border border-emerald-300/80 bg-gradient-to-l from-white via-emerald-50/70 to-emerald-50/60 p-4 text-right shadow-[inset_3px_0_0_#10B981,0_0_0_1px_rgba(16,185,129,0.10),0_10px_24px_rgba(15,23,42,0.06)] dark:border-emerald-500/30 dark:bg-slate-900/80">
            <p className="text-xs font-extrabold text-muted dark:text-slate-400">مبلغ نهایی</p>
            <p className="mt-1 text-3xl font-black tracking-[-0.05em] text-emerald-700 dark:text-emerald-200">
              {formatMoney(expenseFinalTotalMinor)}
            </p>
          </div>

          <Button onClick={handleCreateExpense} disabled={expenseSaving || members.length === 0 || isArchived} className="h-12 w-full text-base">
            {expenseSaving ? (
              <InlineLoader label={receiptFile ? 'آپلود و ثبت...' : 'در حال ثبت...'} />
            ) : (
              <>
                <Plus className="h-5 w-5" />
                ثبت هزینه
              </>
            )}
          </Button>
        </div>
      </Modal>

      <Modal
        open={modal === 'settlement'}
        onClose={() => setModal(null)}
        title="جزئیات تسویه"
        icon={<HandCoins className="h-5 w-5" />}
        size="lg"
      >
        <div className="space-y-4 text-right">
          <div className="dashboard-section-card dashboard-section-card--quiet rounded-[22px] border border-emerald-300/80 bg-gradient-to-l from-white via-emerald-50/80 to-emerald-50/70 p-4 text-right shadow-[0_12px_30px_rgba(15,23,42,0.07)] dark:border-emerald-500/20 dark:bg-slate-900/80">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <h3 className="text-base font-black text-emerald-800 dark:text-emerald-200">تسویه هوشمند</h3>

              <Button
                tone="primary"
                onClick={() => void refreshSmartSettlement()}
                disabled={settlementSaving || isArchived}
                className="h-11 shrink-0 px-4"
              >
                {settlementSaving ? (
                  <InlineLoader label="در حال محاسبه..." />
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4" />
                    محاسبه
                  </>
                )}
              </Button>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <MiniNumberCard label="پرداخت من" value={formatMoney(totalMyDebtMinor)} tone="rose" />
            <MiniNumberCard label="دریافت من" value={formatMoney(totalMyCreditMinor)} tone="emerald" />
            <MiniNumberCard label="خالص حساب من" value={formatSignedMoney(myNetMinor)} tone={accountTone} />
          </div>

          <div className={cn(dashboardQuietCard, 'flex max-h-[460px] flex-col overflow-hidden p-4 text-right')}>
            <h3 className="mb-3 text-right text-sm font-black text-text dark:text-slate-100">ثبت پرداخت</h3>

            <div className={cn(scrollAreaClass, 'flex-1')}>
              {manualPayOptions.length > 0 ? (
                <div className="mb-4 space-y-2">
                  {manualPayOptions.map((item) => {
                    const selected = selectedManualPlanItemId === item.id;
                    const remainingAmount = item.amount_minor;
                    const partialAmount = parseAmountToMinor(manualAmount);
                    const restAfterPartial =
                      selected && manualPaymentMode === 'PARTIAL'
                        ? Math.max(remainingAmount - partialAmount, 0)
                        : remainingAmount;

                    return (
                      <div
                        key={item.id}
                        className={cn(
                          'dashboard-list-row dashboard-list-card rounded-[22px] border p-3 text-right transition',
                          selected
                            ? 'border-emerald-400 bg-emerald-50/80 shadow-[0_12px_28px_rgba(16,185,129,0.10)] dark:border-emerald-400/40 dark:bg-emerald-500/10'
                            : 'border-emerald-200 bg-white/90 hover:border-emerald-300 dark:border-emerald-500/15 dark:bg-slate-900/80 dark:hover:border-emerald-400/30',
                        )}
                      >
                        <button
                          type="button"
                          onClick={() => selectManualPlanItem(item)}
                          className="flex w-full items-center justify-between gap-3 text-right"
                        >
                          <span
                            className={cn(
                              'flex h-8 w-8 items-center justify-center rounded-[18px]',
                              selected
                                ? 'bg-emerald-600 text-white dark:bg-emerald-500'
                                : 'bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500',
                            )}
                          >
                            {selected ? <Check className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
                          </span>

                          <div className="min-w-0 flex-1 text-right">
                            <p className="truncate text-sm font-black text-text dark:text-slate-100">
                              پرداخت به {getPlanPartyName(item, 'receiver', members)}
                            </p>
                            <p className="mt-1 text-xs font-semibold text-muted dark:text-slate-400">
                              مانده: {formatMoney(remainingAmount)}
                            </p>
                          </div>
                        </button>

                        {selected ? (
                          <div className="mt-3 space-y-3">
                            <div className="grid grid-cols-2 gap-2">
                              <button
                                type="button"
                                onClick={() => {
                                  setManualPaymentMode('FULL');
                                  setManualAmount(String(item.amount_minor));
                                }}
                                className={cn(
                                  'rounded-[18px] border px-3 py-2 text-xs font-black transition',
                                  manualPaymentMode === 'FULL'
                                    ? 'border-emerald-400 bg-emerald-600 text-white dark:bg-emerald-500'
                                    : 'border-emerald-200 bg-white text-slate-600 hover:bg-emerald-50 dark:border-emerald-500/20 dark:bg-slate-950 dark:text-slate-300 dark:hover:bg-emerald-500/10',
                                )}
                              >
                                پرداخت کامل
                              </button>

                              <button
                                type="button"
                                onClick={() => {
                                  setManualPaymentMode('PARTIAL');
                                  setManualAmount('');
                                }}
                                className={cn(
                                  'rounded-[18px] border px-3 py-2 text-xs font-black transition',
                                  manualPaymentMode === 'PARTIAL'
                                    ? 'border-emerald-400 bg-emerald-600 text-white dark:bg-emerald-500'
                                    : 'border-emerald-200 bg-white text-slate-600 hover:bg-emerald-50 dark:border-emerald-500/20 dark:bg-slate-950 dark:text-slate-300 dark:hover:bg-emerald-500/10',
                                )}
                              >
                                پرداخت بخشی
                              </button>
                            </div>

                            {manualPaymentMode === 'PARTIAL' ? (
                              <div className="space-y-2">
                                <input
                                  dir="rtl"
                                  inputMode="numeric"
                                  value={manualAmount}
                                  onChange={(event) => setManualAmount(event.target.value)}
                                  placeholder="مبلغ"
                                  className={inputClass}
                                />

                                <div className="rounded-[18px] border border-emerald-200 bg-white/90 px-3 py-2 text-right text-xs font-black text-slate-600 dark:border-emerald-500/20 dark:bg-slate-950 dark:text-slate-300">
                                  باقی‌مانده: {formatMoney(restAfterPartial)}
                                </div>
                              </div>
                            ) : null}

                            <input
                              dir="rtl"
                              value={manualDescription}
                              onChange={(event) => setManualDescription(event.target.value)}
                              placeholder="توضیح"
                              className={inputClass}
                            />

                            <Button onClick={() => void handleCreateManualSettlement()} disabled={settlementSaving} className="h-12 w-full text-base">
                              {manualPaymentMode === 'FULL' ? 'گزارش پرداخت کامل' : 'ثبت پرداخت بخشی'}
                            </Button>
                          </div>
                        ) : null}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="dashboard-panel-empty mb-4 rounded-[20px] border border-dashed border-emerald-200 bg-white/70 p-4 text-center text-xs font-bold text-muted dark:border-emerald-500/20 dark:bg-slate-900/70 dark:text-slate-400">
                  پرداختی برای ثبت نداری.
                </div>
              )}

              <div className="rounded-[20px] border border-emerald-200 bg-white/85 p-3 text-right dark:border-emerald-500/20 dark:bg-slate-900/80">
                <h4 className="mb-3 text-right text-xs font-black text-slate-600 dark:text-slate-300">پرداخت آزاد</h4>

                <div className="grid gap-3 sm:grid-cols-3">
                  <select
                    value={manualReceiverId}
                    onChange={(event) => {
                      setSelectedManualPlanItemId('');
                      setManualReceiverId(event.target.value);
                    }}
                    className={inputClass}
                  >
                    <option value="">دریافت‌کننده</option>
                    {members
                      .filter((member) => getMemberUserId(member) !== currentUserId)
                      .map((member) => {
                        const userId = getMemberUserId(member);
                        return (
                          <option key={userId} value={userId}>
                            {getMemberName(member)}
                          </option>
                        );
                      })}
                  </select>

                  <input
                    dir="rtl"
                    inputMode="numeric"
                    value={!selectedManualPlanItemId ? manualAmount : ''}
                    onChange={(event) => {
                      setSelectedManualPlanItemId('');
                      setManualAmount(event.target.value);
                    }}
                    placeholder="مبلغ"
                    className={inputClass}
                  />

                  <input
                    dir="rtl"
                    value={!selectedManualPlanItemId ? manualDescription : ''}
                    onChange={(event) => {
                      setSelectedManualPlanItemId('');
                      setManualDescription(event.target.value);
                    }}
                    placeholder="توضیح"
                    className={inputClass}
                  />
                </div>

                <div className="mt-3 flex justify-start">
                  <Button
                    onClick={() => void handleCreateManualSettlement()}
                    disabled={settlementSaving || Boolean(selectedManualPlanItemId)}
                    className="h-12 min-w-[136px] px-6 text-base"
                  >
                    ثبت
                  </Button>
                </div>
              </div>
            </div>
          </div>

          <div className={cn(dashboardCard, 'flex max-h-[460px] flex-col overflow-hidden p-4 text-right')}>
            <SectionHeader title="همه تسویه‌ها" />

            <div className={cn(scrollAreaClass, 'flex-1')}>
              {settlementLoading ? (
                <div className="dashboard-panel-state flex items-center justify-center gap-2 rounded-[20px] border border-dashed border-emerald-200 bg-white/[0.65] p-6 text-sm font-bold text-muted dark:border-emerald-500/20 dark:bg-slate-900/70 dark:text-slate-400">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  در حال دریافت...
                </div>
              ) : openPlanItems.length === 0 ? (
                <EmptyState
                  title="تسویه‌ای وجود ندارد"
                  description="اگر هزینه‌ای ثبت شده، محاسبه را بزن."
                  icon={<Check className="h-6 w-6" />}
                />
              ) : (
                <div className="space-y-2">
                  {openPlanItems.map((item) => {
                    const isPayer = item.payer_user_id === currentUserId;
                    const isReceiver = item.receiver_user_id === currentUserId;

                    return (
                      <div key={item.id} className={cn(dashboardRow, 'p-4')}>
                        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                          <div className="text-right">
                            <p className="text-sm font-black text-text dark:text-slate-100">
                              {getPlanPartyName(item, 'payer', members)} ← {getPlanPartyName(item, 'receiver', members)}
                            </p>
                            <p className="mt-1 text-xs font-semibold text-muted dark:text-slate-400">{getSettlementStatusLabel(item.status)}</p>
                          </div>

                          <div className="flex flex-wrap items-center justify-start gap-2">
                            <span className="rounded-[18px] border border-orange-200/80 bg-orange-50 px-3 py-2 text-sm font-black text-orange-700 dark:border-orange-500/30 dark:bg-orange-500/10 dark:text-orange-200">
                              {formatMoney(item.amount_minor)}
                            </span>

                            {isPayer && canReportPlanItem(item, settlementPlan) ? (
                              <Button onClick={() => void handlePlanItemAction(item, 'paid')} disabled={settlementSaving} className="min-h-10 px-3 text-xs">
                                پرداخت کردم
                              </Button>
                            ) : null}

                            {isReceiver && canReviewPlanItem(item) ? (
                              <>
                                <Button onClick={() => void handlePlanItemAction(item, 'confirm')} disabled={settlementSaving} className="min-h-10 px-3 text-xs">
                                  گرفتم
                                </Button>

                                <Button tone="danger" onClick={() => void handlePlanItemAction(item, 'reject')} disabled={settlementSaving} className="min-h-10 px-3 text-xs">
                                  نگرفتم
                                </Button>
                              </>
                            ) : null}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {settlements.length > 0 ? (
            <div className={cn(dashboardQuietCard, 'flex max-h-[360px] flex-col overflow-hidden p-4 text-right')}>
              <h3 className="mb-3 text-right text-sm font-black text-text dark:text-slate-100">پرداخت‌های ثبت‌شده</h3>

              <div className={cn(scrollAreaClass, 'flex-1 space-y-2')}>
                {settlements.slice(0, 20).map((settlement) => {
                  const isPayer = settlement.payer_user_id === currentUserId;
                  const isReceiver = settlement.receiver_user_id === currentUserId;

                  return (
                    <div key={settlement.id} className={cn(dashboardRow, 'p-4')}>
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <div className="text-right">
                          <p className="text-sm font-black text-text dark:text-slate-100">
                            {getUserDisplayFromId(settlement.payer_user_id, members)} به {getUserDisplayFromId(settlement.receiver_user_id, members)}
                          </p>
                          <p className="mt-1 text-xs font-semibold text-muted dark:text-slate-400">{getSettlementStatusLabel(settlement.status)}</p>
                        </div>

                        <div className="flex flex-wrap items-center justify-start gap-2">
                          <span className="rounded-[18px] border border-emerald-200 bg-white px-3 py-2 text-sm font-black text-slate-700 dark:border-emerald-500/20 dark:bg-slate-950 dark:text-slate-200">
                            {formatMoney(settlement.amount_minor)}
                          </span>

                          {isReceiver && settlement.status === 'PENDING_CONFIRMATION' ? (
                            <>
                              <Button onClick={() => void handleSettlementAction(settlement, 'confirm')} className="min-h-9 px-3 text-xs">
                                گرفتم
                              </Button>

                              <Button tone="danger" onClick={() => void handleSettlementAction(settlement, 'reject')} className="min-h-9 px-3 text-xs">
                                نگرفتم
                              </Button>
                            </>
                          ) : null}

                          {isPayer && settlement.status === 'PENDING_CONFIRMATION' ? (
                            <Button tone="secondary" onClick={() => void handleSettlementAction(settlement, 'cancel')} className="min-h-9 px-3 text-xs">
                              لغو
                            </Button>
                          ) : null}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : null}
        </div>
      </Modal>

      <Modal
        open={modal === 'settings'}
        onClose={() => setModal(null)}
        title="اطلاعات گروه"
        icon={<Settings className="h-5 w-5" />}
        size="lg"
      >
        <div className="space-y-4 text-right">
          <div className="dashboard-section-card dashboard-section-card--quiet rounded-[22px] border border-emerald-200 bg-emerald-50/55 p-4 text-right dark:border-emerald-500/20 dark:bg-slate-900/80">
            <h3 className="text-lg font-black text-text dark:text-slate-100">{group?.title || 'گروه'}</h3>
            <p className="mt-1 text-xs font-bold text-muted dark:text-slate-400">{toPersianNumber(members.length)} عضو</p>

            {group?.description ? (
              <p className="mt-3 rounded-[18px] border border-emerald-100 bg-white/80 px-3 py-3 text-sm font-semibold leading-7 text-slate-700 dark:border-emerald-500/20 dark:bg-slate-950 dark:text-slate-300">
                {group.description}
              </p>
            ) : (
              <p className="mt-3 rounded-[18px] border border-dashed border-emerald-200 bg-white/70 px-3 py-3 text-sm font-semibold text-muted dark:border-emerald-500/20 dark:bg-slate-950 dark:text-slate-400">
                توضیحی برای گروه ثبت نشده.
              </p>
            )}
          </div>

          <div className="dashboard-section-card dashboard-section-card--quiet rounded-[22px] border border-emerald-300/80 bg-gradient-to-l from-white via-emerald-50/70 to-emerald-50/60 p-4 text-right shadow-[inset_3px_0_0_#10B981,0_0_0_1px_rgba(16,185,129,0.10),0_10px_24px_rgba(15,23,42,0.06)] dark:border-emerald-500/25 dark:bg-slate-900/80">
            <div className="mb-3 flex items-start justify-between gap-3">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[18px] bg-emerald-600 text-white shadow-[0_10px_22px_rgba(16,185,129,0.22)] dark:bg-emerald-500">
                <Link2 className="h-5 w-5" />
              </div>

              <div className="text-right">
                <h3 className="text-base font-black text-emerald-800 dark:text-emerald-200">دعوت عضو جدید</h3>
              </div>
            </div>

            {!invite ? (
              <Button onClick={handleCreateInvite} disabled={inviteLoading || !canManageGroup} className="w-full">
                <Link2 className="h-4 w-4" />
                {inviteLoading ? 'در حال ساخت...' : 'ساخت لینک دعوت'}
              </Button>
            ) : (
              <div className="space-y-3">
                <input
                  readOnly
                  dir="ltr"
                  value={inviteUrl || 'لینکی آماده نیست'}
                  className="h-11 w-full rounded-[18px] border border-emerald-200 bg-white px-3 text-right text-xs font-semibold text-slate-700 outline-none dark:border-emerald-500/20 dark:bg-slate-950 dark:text-slate-200"
                />

                <div className="grid grid-cols-2 gap-2">
                  <Button tone="secondary" onClick={() => void handleCopyInvite()} disabled={!inviteUrl} className="h-10">
                    <Copy className="h-4 w-4" />
                    {copied ? 'کپی شد' : 'کپی لینک'}
                  </Button>

                  <Button tone="danger" onClick={() => void handleRevokeInvite()} className="h-10">
                    <Trash2 className="h-4 w-4" />
                    لغو لینک
                  </Button>
                </div>
              </div>
            )}
          </div>

          <div className={cn(dashboardCard, 'flex max-h-[430px] flex-col overflow-hidden p-4 text-right')}>
            <SectionHeader title="اعضا" />

            <div className={cn(scrollAreaClass, 'flex-1')}>
              {membersLoading ? (
                <div className="dashboard-panel-state flex items-center justify-center gap-2 rounded-[20px] border border-dashed border-emerald-200 bg-white/[0.65] p-5 text-sm font-bold text-muted dark:border-emerald-500/20 dark:bg-slate-900/70 dark:text-slate-400">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  در حال دریافت اعضا...
                </div>
              ) : (
                <div className="space-y-2">
                  {members.map((member) => {
                    const memberId = getMemberId(member);
                    const userId = getMemberUserId(member);
                    const isSelf = userId === currentUserId;
                    const memberIsOwner = member.role === 'OWNER';
                    const canRemoveMember = canManageGroup && !isSelf && member.role !== 'OWNER';

                    return (
                      <div key={memberId || userId} className={cn(dashboardRow, 'p-3')}>
                        <div className="flex items-center justify-between gap-3">
                          <div className="flex shrink-0 items-center gap-2">
                            <span
                              className={cn(
                                'inline-flex items-center gap-1 rounded-full border px-3 py-1.5 text-xs font-black',
                                memberIsOwner
                                  ? 'border-orange-200 bg-orange-50 text-orange-700 dark:border-orange-500/30 dark:bg-orange-500/10 dark:text-orange-200'
                                  : 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-200',
                              )}
                            >
                              {getRoleLabel(member.role)}
                            </span>

                            {canRemoveMember ? (
                              <button
                                type="button"
                                onClick={() => void handleRemoveMember(member)}
                                className="flex h-9 w-9 items-center justify-center rounded-[18px] border border-rose-200 bg-rose-50 text-rose-600 hover:bg-rose-100 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-200 dark:hover:bg-rose-500/15"
                                aria-label="حذف عضو"
                              >
                                <UserMinus className="h-4 w-4" />
                              </button>
                            ) : null}
                          </div>

                          <div className="flex min-w-0 items-center gap-3 text-right">
                            <div className="min-w-0 text-right">
                              <p className="truncate text-sm font-black text-text dark:text-slate-100">
                                {getMemberName(member)} {isSelf ? '(شما)' : ''}
                              </p>
                              <p className="mt-1 truncate text-xs font-semibold text-muted dark:text-slate-400">
                                {getMemberPhone(member) || 'بدون شماره'}
                              </p>
                            </div>

                            <MemberAvatar name={getMemberName(member)} owner={memberIsOwner} />
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {balances.length > 0 ? (
            <div className={cn(dashboardQuietCard, 'flex max-h-[360px] flex-col overflow-hidden p-4 text-right')}>
              <SectionHeader title="حساب اعضا" />

              <div className={cn(scrollAreaClass, 'flex-1')}>
                <div className="space-y-2">
                  {balances.map((balance) => {
                    const amount = balance.net_balance_minor || 0;

                    return (
                      <div key={balance.user_id} className={cn(dashboardRow, 'flex items-center justify-between gap-3 px-3 py-3 text-sm font-bold')}>
                        <span className="truncate text-text dark:text-slate-100">{getBalanceDisplayName(balance, members)}</span>
                        <span
                          className={
                            amount < 0
                              ? 'text-rose-600 dark:text-rose-200'
                              : amount > 0
                                ? 'text-emerald-600 dark:text-emerald-200'
                                : 'text-slate-600 dark:text-slate-300'
                          }
                        >
                          {formatSignedMoney(amount)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          ) : null}

          {canManageGroup ? (
            <div className={cn(dashboardQuietCard, 'max-h-[420px] overflow-y-auto space-y-4 p-4 text-right')}>
              <Field label="عنوان گروه">
                <input
                  dir="rtl"
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  disabled={!canManageGroup}
                  className={inputClass}
                />
              </Field>

              <Field label="توضیحات">
                <textarea
                  dir="rtl"
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  disabled={!canManageGroup}
                  className={textareaClass}
                />
              </Field>

              <div className="grid gap-2 sm:grid-cols-2">
                <Button onClick={handleSave} disabled={saving || !canManageGroup} className="h-12">
                  {saving ? (
                    <InlineLoader label="در حال ذخیره..." />
                  ) : (
                    <>
                      <Save className="h-4 w-4" />
                      ذخیره
                    </>
                  )}
                </Button>

                {isArchived ? (
                  <Button tone="secondary" onClick={handleRestore} disabled={archiveLoading} className="h-12">
                    <RotateCcw className="h-4 w-4" />
                    فعال‌سازی
                  </Button>
                ) : (
                  <Button tone="secondary" onClick={handleArchive} disabled={archiveLoading || !canManageGroup} className="h-12">
                    <Archive className="h-4 w-4" />
                    آرشیو
                  </Button>
                )}
              </div>
            </div>
          ) : null}

          {!isOwner ? (
            <Button tone="danger" onClick={handleLeave} disabled={leaveLoading} className="h-12 w-full">
              <LogOut className="h-4 w-4" />
              {leaveLoading ? 'در حال خروج...' : 'خروج از گروه'}
            </Button>
          ) : null}
        </div>
      </Modal>

      <Modal
        open={modal === 'activity'}
        onClose={() => setModal(null)}
        title="همه هزینه‌ها"
        icon={<ReceiptText className="h-5 w-5" />}
        size="lg"
      >
        <div className="max-h-[70vh] overflow-y-auto">
          {recentExpenses.length === 0 ? (
            <EmptyState
              title="هزینه‌ای ثبت نشده"
              description="اولین هزینه را ثبت کن."
              icon={<ReceiptText className="h-6 w-6" />}
            />
          ) : (
            <div className="space-y-2 text-right">
              {recentExpenses.map((expense) => {
                const receiptId = (expense as BackendExpense & { receipt_file_id?: string }).receipt_file_id;
                const isOpening = Boolean(receiptId && openingReceiptId === receiptId);

                return (
                  <div key={expense.id} className={cn(dashboardRow, 'p-4')}>
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <div className="min-w-0 text-right">
                        <p className="truncate text-sm font-black text-text dark:text-slate-100">{expense.title}</p>

                        <MetaTags
                          user={getUserDisplayFromId(expense.payer_user_id, members)}
                          date={toPersianDate(expense.expense_date || expense.created_at)}
                        />

                        {expense.description ? (
                          <p className="mt-2 line-clamp-2 text-right text-xs font-semibold leading-6 text-slate-600 dark:text-slate-400">
                            {expense.description}
                          </p>
                        ) : null}
                      </div>

                      <div className="flex shrink-0 flex-wrap items-center justify-start gap-2">
                        <span className="rounded-[18px] border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-black text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-200">
                          {formatMoney(getExpenseTotal(expense))}
                        </span>

                        {receiptId ? (
                          <Button
                            tone="secondary"
                            onClick={() => void handleOpenReceipt(receiptId)}
                            disabled={isOpening}
                            className="min-h-10 px-3 text-xs"
                          >
                            {isOpening ? <Loader2 className="h-4 w-4 animate-spin" /> : <Eye className="h-4 w-4" />}
                            رسید
                          </Button>
                        ) : null}

                        <Button
                          tone="danger"
                          onClick={() => void handleDeleteExpense(expense)}
                          className="min-h-10 px-3 text-xs"
                        >
                          <Trash2 className="h-4 w-4" />
                          حذف
                        </Button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </Modal>
    </main>
  );
}
