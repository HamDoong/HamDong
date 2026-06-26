import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import {
  Archive,
  ArrowLeft,
  Check,
  Copy,
  Crown,
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
} from '../lib/expenseApi';
import {
  activateSettlementPlan,
  cancelSettlement,
  confirmPlanItem,
  confirmSettlement,
  createGroupSettlement,
  generateSettlementPlan,
  getGroupBalances,
  getGroupDebts,
  getMyGroupBalance,
  getSettlementPlan,
  listGroupSettlements,
  rejectPlanItem,
  rejectSettlement,
  reportPlanItemPaid,
  type BalanceItem,
  type DebtItem,
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
import { getCurrentUser, type CurrentUser } from '../lib/userApi';

interface GroupDetailPageProps {
  groupId: string;
  onBack: () => void;
  onGroupUpdated: (group: BackendGroup) => void;
  onGroupRemoved: (groupId: string) => void;
}

type QuickSection = 'expense-card' | 'members-card' | 'settlement-card' | 'settings-card';
type VisualTone = 'neutral' | 'positive' | 'negative' | 'warning' | 'sky' | 'slate';

function cn(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(' ');
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

function getBackendMessage(error: unknown) {
  return getFriendlyApiErrorMessage(error, {
    defaultMessage: 'عملیات انجام نشد. لطفاً دوباره تلاش کن.',
    invalidMessage: 'اطلاعات واردشده کامل یا درست نیست.',
  });
}

function toPersianNumber(value: string | number) {
  return String(value).replace(/\d/g, (digit) => '۰۱۲۳۴۵۶۷۸۹'[Number(digit)]);
}

function formatMoney(minor = 0) {
  const absValue = Math.abs(Math.round(minor));
  return `${toPersianNumber(absValue.toLocaleString('en-US'))} تومان`;
}

function formatSignedMoney(minor = 0) {
  if (minor > 0) return `+${formatMoney(minor)}`;
  if (minor < 0) return `-${formatMoney(minor)}`;
  return formatMoney(0);
}

function getMyAccountStatus(minor = 0) {
  if (minor > 0) {
    return {
      label: 'طلبکار',
      amount: formatMoney(minor),
      tone: 'positive' as const,
    };
  }

  if (minor < 0) {
    return {
      label: 'بدهکار',
      amount: formatMoney(minor),
      tone: 'negative' as const,
    };
  }

  return {
    label: 'تسویه',
    amount: formatMoney(0),
    tone: 'neutral' as const,
  };
}

function getRemainingPaymentsLabel(count: number) {
  if (count <= 0) return 'تسویه';
  return `${toPersianNumber(count)} پرداخت`;
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

function parseAmountToMinor(value: string) {
  const persianDigits = '۰۱۲۳۴۵۶۷۸۹';
  const arabicDigits = '٠١٢٣٤٥٦٧٨٩';

  const normalized = value
    .replace(/[۰-۹]/g, (digit) => String(persianDigits.indexOf(digit)))
    .replace(/[٠-٩]/g, (digit) => String(arabicDigits.indexOf(digit)));

  const digits = normalized.replace(/[^0-9]/g, '');
  return Number(digits || 0);
}

function getExpenseTotal(expense: BackendExpense) {
  return (
    expense.total_amount_minor ??
    (expense.base_amount_minor || 0) +
      (expense.tax_amount_minor || 0) +
      (expense.service_fee_amount_minor || 0)
  );
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

function getCurrentUserId(user: CurrentUser | null) {
  return user?.id ? String(user.id) : '';
}

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

function scrollToSection(id: QuickSection) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function MemberAvatar({ name }: { name: string }) {
  return (
    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border-2 border-emerald-100 bg-gradient-to-br from-emerald-50 via-teal-50 to-white text-sm font-black text-emerald-700 shadow-[inset_3px_0_0_#10B981,0_10px_28px_rgba(15,23,42,0.045)]">
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

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-[22px] border-2 border-dashed border-emerald-100/80 bg-white/[0.58] p-7 text-center shadow-[0_16px_38px_rgba(15,23,42,0.035)]">
      <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-[18px] bg-white text-emerald-600 shadow-sm">
        <Users className="h-6 w-6" />
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

function ActionButton({
  children,
  onClick,
  disabled,
  tone = 'primary',
  className,
}: {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  tone?: 'primary' | 'soft' | 'danger' | 'dark';
  className?: string;
}) {
  const toneClass =
    tone === 'primary'
      ? 'bg-gradient-to-l from-[#00915F] to-[#00A86B] text-white shadow-[0_18px_42px_rgba(0,168,107,0.15)] hover:-translate-y-0.5'
      : tone === 'danger'
        ? 'border-2 border-rose-100 bg-rose-50 text-rose-600 shadow-[0_16px_36px_rgba(244,63,94,0.055)] hover:bg-rose-100'
        : tone === 'dark'
          ? 'bg-slate-900 text-white shadow-[0_16px_36px_rgba(15,23,42,0.12)] hover:bg-slate-800'
          : 'border-2 border-slate-200 bg-white text-slate-700 shadow-[0_14px_32px_rgba(15,23,42,0.045)] hover:bg-slate-50';

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'inline-flex h-11 items-center justify-center gap-2 rounded-[17px] px-4 text-sm font-black transition disabled:cursor-not-allowed disabled:opacity-55 disabled:hover:translate-y-0',
        toneClass,
        className,
      )}
    >
      {children}
    </button>
  );
}

function FieldSurface({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-[24px] border-2 border-emerald-100/80 bg-white/[0.78] p-4 shadow-[0_16px_40px_rgba(15,23,42,0.04)]">
      {children}
    </div>
  );
}

function ListRow({ children, tone = 'emerald' }: { children: ReactNode; tone?: 'emerald' | 'slate' }) {
  const className =
    tone === 'slate'
      ? 'border-slate-200 bg-white/[0.88] hover:border-slate-300'
      : 'border-emerald-100/80 bg-white/[0.86] hover:border-emerald-200';

  return (
    <div
      className={cn(
        'rounded-[22px] border-2 px-4 py-4 text-right transition hover:-translate-y-0.5 hover:bg-white hover:shadow-[0_18px_42px_rgba(15,23,42,0.05)]',
        className,
      )}
    >
      {children}
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
  const autoSettlementKeyRef = useRef('');

  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [group, setGroup] = useState<BackendGroup | null>(null);
  const [members, setMembers] = useState<BackendGroupMember[]>([]);
  const [expenses, setExpenses] = useState<BackendExpense[]>([]);
  const [balances, setBalances] = useState<BalanceItem[]>([]);
  const [myBalance, setMyBalance] = useState<MyBalanceResponse | null>(null);
  const [debts, setDebts] = useState<DebtItem[]>([]);
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
  const [receiptFile, setReceiptFile] = useState<File | null>(null);
  const [openingReceiptId, setOpeningReceiptId] = useState<string | null>(null);

  const [manualReceiverId, setManualReceiverId] = useState('');
  const [manualAmount, setManualAmount] = useState('');
  const [manualDescription, setManualDescription] = useState('');

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
  const [error, setError] = useState<string | null>(null);

  const inviteUrl = useMemo(() => (invite ? getInviteUrl(invite) : ''), [invite]);

  const isArchived = group?.status === 'ARCHIVED';
  const isOwner = group?.my_role === 'OWNER';
  const canManageGroup = ['OWNER', 'ADMIN'].includes(group?.my_role || '');
  const currentUserId = getCurrentUserId(currentUser);

  const activeExpenses = expenses.filter(
    (expense) => expense.status !== 'DELETED' && expense.status !== 'CANCELLED',
  );

  const recentExpenses = [...activeExpenses].sort((a, b) => {
    const left = new Date(a.expense_date || a.created_at || 0).getTime();
    const right = new Date(b.expense_date || b.created_at || 0).getTime();
    return right - left;
  });

  const totalExpenseMinor = activeExpenses.reduce(
    (sum, expense) => sum + getExpenseTotal(expense),
    0,
  );

  const openDebts = debts.filter(
    (debt) => isOpenSettlementStatus(debt.status) && (debt.amount_minor || 0) > 0,
  );

  const optimizedSettlements = useMemo(
    () => calculateOptimizedSettlements(balances, members),
    [balances, members],
  );
  const openPlanItems =
    settlementPlan?.items?.filter((item) => isOpenSettlementStatus(item.status)) || [];

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
  const backendPaymentCount = openDebts.length || openPlanItems.length;
  const currentSuggestedPayment = currentUserOptimizedPayment || null;

  async function loadGroup() {
    try {
      setLoading(true);
      setError(null);

      const backendGroup = await getGroupDetail(groupId);

      setGroup(backendGroup);
      setTitle(backendGroup.title || '');
      setDescription(backendGroup.description || '');
      setGroupType(backendGroup.group_type || 'GENERAL');
      onGroupUpdated(backendGroup);
    } catch (err) {
      console.error(err);
      setError('خطا در دریافت جزئیات گروه');
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
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'دریافت اعضا ناموفق بود',
        description: getBackendMessage(err) || 'لطفاً دوباره تلاش کن.',
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
        description: getBackendMessage(err) || 'لطفاً دوباره تلاش کن.',
      });
    } finally {
      setExpensesLoading(false);
    }
  }

  async function loadSettlementData() {
    try {
      setSettlementLoading(true);

      const [
        balancesResult,
        myBalanceResult,
        debtsResult,
        planResult,
        settlementsResult,
      ] = await Promise.allSettled([
        getGroupBalances(groupId),
        getMyGroupBalance(groupId),
        getGroupDebts(groupId),
        getSettlementPlan(groupId),
        listGroupSettlements(groupId),
      ]);

      setBalances(balancesResult.status === 'fulfilled' ? balancesResult.value.balances || [] : []);
      setMyBalance(myBalanceResult.status === 'fulfilled' ? myBalanceResult.value : null);
      setDebts(debtsResult.status === 'fulfilled' ? debtsResult.value.debts || [] : []);
      setSettlementPlan(planResult.status === 'fulfilled' ? planResult.value : null);
      setSettlements(settlementsResult.status === 'fulfilled' ? settlementsResult.value || [] : []);
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'دریافت تسویه‌ها ناموفق بود',
        description: getBackendMessage(err) || 'لطفاً دوباره تلاش کن.',
      });
    } finally {
      setSettlementLoading(false);
    }
  }

  async function reloadAll() {
    await Promise.all([loadGroup(), loadMembers(), loadExpenses(), loadSettlementData()]);
  }

  async function refreshSmartSettlement(showNotification = true) {
    try {
      setSettlementSaving(true);

      try {
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
      } catch (planError) {
        console.warn('Smart plan generation was skipped; refreshing balances instead:', planError);
      }

      await loadSettlementData();

      if (showNotification) {
        notify({
          type: 'success',
          title: 'حساب کمینه بروزرسانی شد',
          description: 'مانده‌های گروه دوباره دریافت شد و پرداخت نهایی از روی حساب کمینه نمایش داده شد.',
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
    void reloadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groupId]);

  useEffect(() => {
    if (settlementLoading || settlementSaving || expensesLoading || membersLoading) return;
    if (isArchived) return;
    if (members.length < 2) return;
    if (activeExpenses.length === 0 || totalExpenseMinor <= 0) return;

    const autoKey = `${groupId}:${activeExpenses.length}:${totalExpenseMinor}`;

    if (autoSettlementKeyRef.current === autoKey) return;

    autoSettlementKeyRef.current = autoKey;
    void refreshSmartSettlement(false);

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    groupId,
    settlementLoading,
    settlementSaving,
    expensesLoading,
    membersLoading,
    isArchived,
    members.length,
    activeExpenses.length,
    totalExpenseMinor,
  ]);

  async function handleSave() {
    if (!title.trim()) {
      notify({
        type: 'error',
        title: 'عنوان گروه لازم است',
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

      notify({
        type: 'success',
        title: 'تغییرات ذخیره شد',
        description: 'اطلاعات گروه بروزرسانی شد.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'ویرایش گروه ناموفق بود',
        description: getBackendMessage(err) || 'لطفاً دوباره تلاش کن.',
      });
    } finally {
      setSaving(false);
    }
  }

  async function handleArchive() {
    if (isArchived) return;

    const confirmed = await confirm({
      title: 'آرشیو گروه؟',
      description: 'گروه از لیست فعال‌ها خارج می‌شود، اما اطلاعاتش باقی می‌ماند.',
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
        description: 'این گروه دیگر در لیست فعال‌ها نمایش داده نمی‌شود.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'آرشیو گروه ناموفق بود',
        description: getBackendMessage(err) || 'لطفاً دوباره تلاش کن.',
      });
    } finally {
      setArchiveLoading(false);
    }
  }

  async function handleRestore() {
    if (!isArchived) return;

    const confirmed = await confirm({
      title: 'بازگردانی گروه؟',
      description: 'گروه دوباره به لیست گروه‌های فعال برمی‌گردد.',
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
        description: 'گروه دوباره در لیست فعال‌هاست.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'بازگردانی گروه ناموفق بود',
        description: getBackendMessage(err) || 'لطفاً دوباره تلاش کن.',
      });
    } finally {
      setArchiveLoading(false);
    }
  }

  async function handleLeave() {
    if (isOwner) {
      notify({
        type: 'info',
        title: 'مالک گروه نمی‌تواند خارج شود',
        description: 'اول مالکیت را منتقل کن یا گروه را آرشیو کن.',
      });
      return;
    }

    const confirmed = await confirm({
      title: 'خروج از گروه؟',
      description: 'بعد از خروج، این گروه از لیست تو حذف می‌شود.',
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
        title: 'از گروه خارج شدی',
        description: 'گروه از لیست تو حذف شد.',
      });

      onGroupRemoved(groupId);
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'خروج از گروه ناموفق بود',
        description: getBackendMessage(err) || 'لطفاً دوباره تلاش کن.',
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
        description: 'اطلاعات این عضو کامل نیست.',
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
        description: 'این عضو دیگر در گروه نیست.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'حذف عضو ناموفق بود',
        description: getBackendMessage(err) || 'لطفاً دوباره تلاش کن.',
      });
    }
  }

  function toggleExpenseParticipant(userId: string) {
    setExpenseParticipantIds((prev) =>
      prev.includes(userId) ? prev.filter((item) => item !== userId) : [...prev, userId],
    );
  }

  async function handleCreateExpense() {
    const amountMinor = parseAmountToMinor(expenseAmount);

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

    if (!amountMinor || amountMinor <= 0) {
      notify({
        type: 'error',
        title: 'مبلغ معتبر نیست',
        description: 'مبلغ هزینه را به عدد وارد کن.',
      });
      return;
    }

    if (!expensePayerId) {
      notify({
        type: 'error',
        title: 'پرداخت‌کننده مشخص نیست',
        description: 'یک عضو را به عنوان پرداخت‌کننده انتخاب کن.',
      });
      return;
    }

    if (expenseParticipantIds.length === 0) {
      notify({
        type: 'error',
        title: 'اعضای تقسیم مشخص نیستند',
        description: 'حداقل یک عضو را برای تقسیم هزینه انتخاب کن.',
      });
      return;
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
        base_amount_minor: amountMinor,
        currency: 'IRR',
        split_method: 'EQUAL',
        participant_user_ids: expenseParticipantIds,
        receipt_file_id: receiptFileId,
      });

      setExpenseTitle('');
      setExpenseAmount('');
      setExpenseDescription('');
      setReceiptFile(null);

      await Promise.all([loadExpenses(), loadSettlementData()]);

      notify({
        type: 'success',
        title: 'هزینه ثبت شد',
        description: 'محاسبه هوشمند بروزرسانی می‌شود.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'ثبت هزینه ناموفق بود',
        description: getBackendMessage(err) || 'لطفاً دوباره تلاش کن.',
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
        title: 'مشاهده رسید ناموفق بود',
        description: getBackendMessage(err) || 'فایل رسید باز نشد. دوباره تلاش کن.',
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

      notify({
        type: 'success',
        title: 'هزینه حذف شد',
        description: 'محاسبه هوشمند بروزرسانی می‌شود.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'حذف هزینه ناموفق بود',
        description: getBackendMessage(err) || 'لطفاً دوباره تلاش کن.',
      });
    }
  }

  async function handleCreateManualSettlement(receiverUserId?: string, amountMinor?: number) {
    const targetReceiverId = receiverUserId || manualReceiverId;
    const targetAmountMinor = amountMinor ?? parseAmountToMinor(manualAmount);
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
        title: 'دریافت‌کننده را انتخاب کن',
        description: 'از پیشنهادهای تسویه یا لیست اعضا، کسی را که باید پول بگیرد انتخاب کن.',
      });
      return;
    }

    if (targetReceiverId === currentUserId) {
      notify({
        type: 'error',
        title: 'پرداخت به خودت ممکن نیست',
        description: 'برای تسویه باید یکی دیگر از اعضای گروه را انتخاب کنی.',
      });
      return;
    }

    if (!targetAmountMinor || targetAmountMinor <= 0) {
      notify({
        type: 'error',
        title: 'مبلغ پرداخت را وارد کن',
        description: 'مبلغ باید عددی و بیشتر از صفر باشد؛ مثلاً ۲۰۰۰۰.',
      });
      return;
    }

    if (!receiverUserId && targetSuggestion && targetAmountMinor > targetSuggestion.amount_minor) {
      notify({
        type: 'info',
        title: 'مبلغ بیشتر از پیشنهاد تسویه است',
        description: `برای این عضو، مبلغ پیشنهادی ${formatMoney(targetSuggestion.amount_minor)} است. مبلغ را اصلاح کن یا از دکمه پیشنهاد استفاده کن.`,
      });
      return;
    }

    try {
      setSettlementSaving(true);

      await createGroupSettlement(groupId, {
        receiver_user_id: targetReceiverId,
        amount_minor: targetAmountMinor,
        currency: 'IRR',
        description: manualDescription || 'تسویه دستی در گروه',
      });

      setManualReceiverId('');
      setManualAmount('');
      setManualDescription('');

      await loadSettlementData();

      notify({
        type: 'success',
        title: 'پرداخت ثبت شد',
        description: 'در انتظار تأیید دریافت‌کننده قرار گرفت.',
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

  async function handlePlanItemAction(
    item: SettlementPlanItem,
    action: 'paid' | 'confirm' | 'reject',
  ) {
    try {
      setSettlementSaving(true);

      if (action === 'paid') await reportPlanItemPaid(item.id);
      if (action === 'confirm') await confirmPlanItem(item.id);
      if (action === 'reject') await rejectPlanItem(item.id);

      await loadSettlementData();

      notify({
        type: 'success',
        title: 'وضعیت پرداخت بروزرسانی شد',
        description: 'اطلاعات جدید نمایش داده شد.',
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

  async function handleSettlementAction(
    settlement: SettlementItem,
    action: 'confirm' | 'reject' | 'cancel',
  ) {
    try {
      setSettlementSaving(true);

      if (action === 'confirm') await confirmSettlement(settlement.id);
      if (action === 'reject') await rejectSettlement(settlement.id);
      if (action === 'cancel') await cancelSettlement(settlement.id);

      await loadSettlementData();

      notify({
        type: 'success',
        title: 'پرداخت بروزرسانی شد',
        description: 'لیست پرداخت‌ها بروزرسانی شد.',
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
        title: 'لینک دعوت ساخته شد',
        description: 'لینک را کپی کن و برای عضو جدید بفرست.',
      });
    } catch (err) {
      console.error(err);

      const permissionDenied = isApiError(err) && err.status === 403;

      notify({
        type: 'error',
        title: permissionDenied
          ? 'امکان ساخت لینک دعوت وجود ندارد'
          : 'ساخت لینک دعوت انجام نشد',
        description: permissionDenied
          ? 'شما مدیر گروه نیستید و اجازه ساخت لینک دعوت را ندارید.'
          : getBackendMessage(err),
      });
    } finally {
      setInviteLoading(false);
    }
  }

  async function handleCopyInvite() {
    if (!inviteUrl) {
      notify({
        type: 'error',
        title: 'لینک دعوت موجود نیست',
        description: 'لینک آماده نشد. دوباره تلاش کن.',
      });
      return;
    }

    try {
      await navigator.clipboard.writeText(inviteUrl);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);

      notify({
        type: 'success',
        title: 'لینک کپی شد',
        description: 'حالا می‌تونی لینک را برای عضو جدید بفرستی.',
      });
    } catch {
      setCopied(false);
      notify({
        type: 'error',
        title: 'کپی لینک ناموفق بود',
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
        title: 'لغو دعوت انجام نشد',
        description: 'اطلاعات لازم برای لغو کامل نیست.',
      });
      return;
    }

    const confirmed = await confirm({
      title: 'لغو لینک دعوت؟',
      description: 'بعد از لغو، این لینک دیگر قابل استفاده نیست.',
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
        title: 'لینک دعوت لغو شد',
        description: 'این دعوت دیگر فعال نیست.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'لغو دعوت ناموفق بود',
        description: getBackendMessage(err) || 'لطفاً دوباره تلاش کن.',
      });
    }
  }

  return (
    <main className="px-4 py-4 sm:px-6 sm:py-5 xl:px-8" dir="rtl">
      <div className="mx-auto max-w-[1280px] space-y-5">
        <section className="rounded-[30px] border-2 border-emerald-100/80 bg-white/95 p-4 shadow-[0_26px_64px_rgba(15,23,42,0.065)] backdrop-blur sm:p-5">
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_420px] lg:items-center" dir="ltr">
            <div className="flex flex-wrap items-center gap-2 lg:justify-start">
              <button
                type="button"
                onClick={onBack}
                className="inline-flex h-11 items-center gap-2 rounded-[16px] border-2 border-emerald-100 bg-emerald-50/60 px-4 text-sm font-black text-emerald-700 transition hover:-translate-y-0.5 hover:border-emerald-200 hover:bg-white"
              >
                <ArrowLeft className="h-4 w-4" />
                بازگشت
              </button>

              {isArchived ? (
                <ActionButton tone="soft" onClick={handleRestore} disabled={archiveLoading}>
                  {archiveLoading ? (
                    <InlineLoader label="در حال فعال‌سازی..." />
                  ) : (
                    <>
                      <RotateCcw className="h-4 w-4" />
                      فعال‌سازی
                    </>
                  )}
                </ActionButton>
              ) : (
                <ActionButton tone="soft" onClick={handleArchive} disabled={archiveLoading}>
                  {archiveLoading ? (
                    <InlineLoader label="در حال آرشیو..." />
                  ) : (
                    <>
                      <Archive className="h-4 w-4" />
                      آرشیو
                    </>
                  )}
                </ActionButton>
              )}

              {!isOwner ? (
                <ActionButton tone="danger" onClick={handleLeave} disabled={leaveLoading}>
                  <LogOut className="h-4 w-4" />
                  {leaveLoading ? 'در حال خروج...' : 'خروج'}
                </ActionButton>
              ) : null}
            </div>

            <div className="min-w-0 text-center lg:text-right" dir="rtl">
              <h1 className="truncate text-[30px] font-black leading-tight tracking-[-0.03em] text-text sm:text-[36px]">
                {loading ? 'در حال دریافت گروه...' : group?.title || 'جزئیات گروه'}
              </h1>
            </div>
          </div>

          <div className="mt-4 grid gap-3 xl:grid-cols-[minmax(0,1fr)_420px] xl:items-stretch" dir="ltr">
            <div className="flex min-h-[104px] items-center rounded-[24px] border-2 border-emerald-100/80 bg-white/[0.72] p-2.5 shadow-[0_18px_42px_rgba(15,23,42,0.04)]">
              <div className="grid w-full grid-cols-2 place-items-center gap-2.5 sm:grid-cols-4">
                <QuickActionButton
                  id="expense-card"
                  label="ثبت هزینه"
                  icon={<ReceiptText className="h-5 w-5" />}
                  tone="emerald"
                />

                <QuickActionButton
                  id="members-card"
                  label="اعضا"
                  icon={<Users className="h-5 w-5" />}
                  tone="sky"
                />

                <QuickActionButton
                  id="settlement-card"
                  label="تسویه"
                  icon={<HandCoins className="h-5 w-5" />}
                  tone="orange"
                />

                <QuickActionButton
                  id="settings-card"
                  label="تنظیمات"
                  icon={<Settings className="h-5 w-5" />}
                  tone="slate"
                />
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2" dir="rtl">
              <HeaderMiniCard
                label="حساب من"
                status={myAccount.label}
                value={myAccount.amount}
                icon={<HandCoins className="h-4 w-4" />}
                tone={myAccount.tone}
              />

              <HeaderMiniCard
                label="هزینه کل"
                value={formatMoney(totalExpenseMinor)}
                status={`${toPersianNumber(activeExpenses.length)} هزینه`}
                icon={<ReceiptText className="h-4 w-4" />}
                tone="positive"
              />
            </div>
          </div>
        </section>

        {error ? (
          <div className="rounded-[24px] border-2 border-rose-100 bg-rose-50 p-4 text-center text-sm font-black text-rose-600 shadow-[0_16px_38px_rgba(244,63,94,0.045)]">
            {error}
          </div>
        ) : null}

        <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_370px]">
          <section className="space-y-5">
            <SectionCard
              id="expense-card"
              title="ثبت هزینه سریع"
              icon={<ReceiptText className="h-5 w-5" />}
              accent="emerald"
            >
              <FieldSurface>
                <div className="grid gap-4 md:grid-cols-2">
                  <label className="block text-right">
                    <span className="mb-2 block text-sm font-black text-text">عنوان هزینه</span>
                    <input
                      dir="rtl"
                      value={expenseTitle}
                      onChange={(event) => setExpenseTitle(event.target.value)}
                      placeholder="مثلاً شام، تاکسی، خرید..."
                      className="h-12 w-full rounded-[18px] border-2 border-emerald-100 bg-white/80 px-4 text-sm font-bold text-text outline-none transition placeholder:text-slate-400 focus:border-emerald-300 focus:bg-white focus:ring-4 focus:ring-emerald-500/10"
                    />
                  </label>

                  <label className="block text-right">
                    <span className="mb-2 block text-sm font-black text-text">مبلغ</span>
                    <input
                      dir="rtl"
                      inputMode="numeric"
                      value={expenseAmount}
                      onChange={(event) => setExpenseAmount(event.target.value)}
                      placeholder="مثلاً ۲۵۰٬۰۰۰"
                      className="h-12 w-full rounded-[18px] border-2 border-emerald-100 bg-white/80 px-4 text-sm font-bold text-text outline-none transition placeholder:text-slate-400 focus:border-emerald-300 focus:bg-white focus:ring-4 focus:ring-emerald-500/10"
                    />
                  </label>

                  <label className="block text-right">
                    <span className="mb-2 block text-sm font-black text-text">پرداخت‌کننده</span>
                    <select
                      value={expensePayerId}
                      onChange={(event) => setExpensePayerId(event.target.value)}
                      className="h-12 w-full rounded-[18px] border-2 border-emerald-100 bg-white/80 px-4 text-sm font-bold text-text outline-none transition focus:border-emerald-300 focus:bg-white focus:ring-4 focus:ring-emerald-500/10"
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
                  </label>

                  <label className="block text-right">
                    <span className="mb-2 block text-sm font-black text-text">رسید اختیاری</span>
                    <div className="relative flex min-h-12 items-center rounded-[18px] border-2 border-emerald-100 bg-white/80 px-3 py-2 transition focus-within:border-emerald-300 focus-within:bg-white focus-within:ring-4 focus-within:ring-emerald-500/10">
                      <Upload className="ml-2 h-4 w-4 text-emerald-600" />
                      <input
                        type="file"
                        accept="image/png,image/jpeg,image/jpg,image/webp,application/pdf"
                        onChange={(event) => setReceiptFile(event.target.files?.[0] || null)}
                        className="w-full text-xs font-bold text-slate-600 file:ml-3 file:rounded-[12px] file:border-0 file:bg-emerald-50 file:px-3 file:py-2 file:text-xs file:font-black file:text-emerald-700"
                      />
                    </div>
                  </label>
                </div>

                {receiptFile ? (
                  <div className="mt-3 flex items-center justify-between gap-3 rounded-[18px] border-2 border-emerald-100 bg-emerald-50 px-4 py-3 text-sm font-bold text-emerald-700 shadow-[inset_3px_0_0_#10B981]">
                    <span className="min-w-0 truncate">رسید انتخاب‌شده: {receiptFile.name}</span>
                    <button
                      type="button"
                      onClick={() => setReceiptFile(null)}
                      className="shrink-0 rounded-full bg-white p-1 text-rose-500 shadow-sm"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ) : null}

                <label className="mt-4 block text-right">
                  <span className="mb-2 block text-sm font-black text-text">توضیح اختیاری</span>
                  <textarea
                    dir="rtl"
                    value={expenseDescription}
                    onChange={(event) => setExpenseDescription(event.target.value)}
                    placeholder="اگر خواستی توضیح کوتاهی بنویس..."
                    className="min-h-[86px] w-full resize-none rounded-[18px] border-2 border-emerald-100 bg-white/80 px-4 py-3 text-sm font-semibold leading-7 text-text outline-none transition placeholder:text-slate-400 focus:border-emerald-300 focus:bg-white focus:ring-4 focus:ring-emerald-500/10"
                  />
                </label>
              </FieldSurface>

              <div className="mt-4 rounded-[24px] border-2 border-sky-100/80 bg-gradient-to-l from-white via-sky-50/70 to-sky-50/40 p-4 shadow-[inset_3px_0_0_#0EA5E9,0_16px_38px_rgba(14,165,233,0.04)]">
                <div className="mb-3 flex items-center justify-between gap-3 text-right">
                  <h3 className="text-sm font-black text-text">تقسیم بین اعضا</h3>

                  <span className="rounded-full bg-white px-3 py-1 text-xs font-black text-sky-700 shadow-sm">
                    {toPersianNumber(expenseParticipantIds.length)} نفر
                  </span>
                </div>

                {membersLoading ? (
                  <div className="flex items-center justify-center gap-2 rounded-[18px] bg-white p-4 text-sm font-bold text-muted shadow-sm">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    در حال دریافت اعضا...
                  </div>
                ) : null}

                <div className="grid gap-2 sm:grid-cols-2">
                  {members.map((member) => {
                    const userId = getMemberUserId(member);
                    const selected = expenseParticipantIds.includes(userId);

                    return (
                      <button
                        key={userId}
                        type="button"
                        onClick={() => toggleExpenseParticipant(userId)}
                        className={cn(
                          'flex items-center justify-between rounded-[18px] border-2 px-3 py-3 text-right text-sm font-black transition hover:-translate-y-0.5',
                          selected
                            ? 'border-sky-200 bg-white text-sky-700 shadow-[inset_3px_0_0_#0EA5E9,0_12px_28px_rgba(14,165,233,0.04)]'
                            : 'border-slate-200 bg-white/75 text-slate-600 hover:border-sky-200 hover:bg-white',
                        )}
                      >
                        <span>{getMemberName(member)}</span>
                        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-white text-sky-600 shadow-sm">
                          {selected ? <Check className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="mt-5 flex justify-end">
                <ActionButton
                  onClick={handleCreateExpense}
                  disabled={expenseSaving || members.length === 0 || isArchived}
                  className="h-12 px-6"
                >
                  {expenseSaving ? (
                    <InlineLoader
                      label={receiptFile ? 'در حال آپلود و ثبت...' : 'در حال ثبت...'}
                    />
                  ) : (
                    <>
                      <Plus className="h-4 w-4" />
                      ثبت هزینه
                    </>
                  )}
                </ActionButton>
              </div>
            </SectionCard>

            <SectionCard
              title="هزینه‌های اخیر"
              icon={<ReceiptText className="h-5 w-5" />}
              accent="slate"
            >
              {expensesLoading ? (
                <div className="flex items-center justify-center gap-2 rounded-[22px] border-2 border-slate-100 bg-slate-50 p-6 text-center text-sm font-bold text-muted">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  در حال دریافت هزینه‌ها...
                </div>
              ) : null}

              {!expensesLoading && recentExpenses.length === 0 ? (
                <EmptyState
                  title="هنوز هزینه‌ای ثبت نشده"
                  description="اولین هزینه را از بخش ثبت هزینه سریع وارد کن."
                />
              ) : null}

              <div className="space-y-3">
                {recentExpenses.slice(0, 10).map((expense) => {
                  const payerName = getUserDisplayFromId(expense.payer_user_id, members);

                  return (
                    <ListRow key={expense.id}>
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <div className="min-w-0 text-right">
                          <div className="truncate text-base font-black text-text">
                            {expense.title}
                          </div>

                          <div className="mt-1 text-xs font-bold leading-6 text-muted">
                            پرداخت‌کننده: {payerName} •{' '}
                            {toPersianDate(expense.expense_date || expense.created_at)}
                          </div>

                          {expense.description ? (
                            <div className="mt-1 line-clamp-2 text-xs font-semibold leading-6 text-slate-500">
                              {expense.description}
                            </div>
                          ) : null}
                        </div>

                        <div className="flex shrink-0 flex-wrap items-center gap-2 sm:justify-end">
                          <span className="rounded-[16px] border-2 border-emerald-100 bg-emerald-50 px-3 py-2 text-sm font-black text-emerald-700 shadow-sm">
                            {formatMoney(getExpenseTotal(expense))}
                          </span>

                          {expense.receipt_file_id ? (
                            <button
                              type="button"
                              onClick={() => void handleOpenReceipt(expense.receipt_file_id)}
                              disabled={openingReceiptId === expense.receipt_file_id}
                              className="inline-flex h-10 items-center justify-center gap-2 rounded-[15px] border-2 border-sky-100 bg-sky-50 px-3 text-xs font-black text-sky-700 transition hover:bg-sky-100 disabled:opacity-60"
                            >
                              {openingReceiptId === expense.receipt_file_id ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <Eye className="h-4 w-4" />
                              )}
                              رسید
                            </button>
                          ) : null}

                          <button
                            type="button"
                            onClick={() => handleDeleteExpense(expense)}
                            className="inline-flex h-10 items-center justify-center gap-2 rounded-[15px] border-2 border-rose-100 bg-rose-50 px-3 text-xs font-black text-rose-600 transition hover:bg-rose-100"
                          >
                            <Trash2 className="h-4 w-4" />
                            حذف
                          </button>
                        </div>
                      </div>
                    </ListRow>
                  );
                })}
              </div>
            </SectionCard>

            <SectionCard
              id="settlement-card"
              title="تسویه حساب"
              icon={<HandCoins className="h-5 w-5" />}
              accent="orange"
              badge={
                <button
                  type="button"
                  onClick={() => void refreshSmartSettlement(true)}
                  disabled={settlementSaving || settlementLoading || isArchived}
                  className="inline-flex h-10 items-center justify-center gap-2 rounded-[16px] border-2 border-orange-100 bg-orange-50 px-3 text-xs font-black text-orange-700 shadow-sm transition hover:-translate-y-0.5 hover:border-orange-200 hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {settlementSaving ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <RefreshCw className="h-4 w-4" />
                  )}
                  دوباره حساب کن
                </button>
              }
            >
              {settlementLoading ? (
                <div className="flex items-center justify-center gap-2 rounded-[22px] border-2 border-orange-100 bg-orange-50 p-6 text-center text-sm font-bold text-orange-700">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  در حال حساب کردن...
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="grid gap-3 md:grid-cols-2">
                    <AccountStatusBox amount={myNetMinor} />

                    <RemainingPaymentsBox
                      count={remainingPaymentCount}
                      totalMinor={totalOpenDebtMinor}
                      tone={myAccount.tone}
                    />
                  </div>


                  <div className="rounded-[24px] border-2 border-orange-200/80 bg-gradient-to-l from-white via-orange-50/70 to-orange-50/50 p-4 shadow-[inset_3px_0_0_#F97316,0_18px_44px_rgba(249,115,22,0.055)]">
                    <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div className="text-right">
                        <h3 className="text-base font-black text-text">
                          پیشنهاد تسویه کمینه
                        </h3>
                      </div>

                      {remainingPaymentCount > 0 ? (
                        <span className="shrink-0 rounded-full bg-white px-3 py-1 text-xs font-black text-orange-700 shadow-sm">
                          {toPersianNumber(remainingPaymentCount)} پرداخت نهایی
                        </span>
                      ) : null}
                    </div>

                    {backendPaymentCount > remainingPaymentCount && remainingPaymentCount > 0 ? (
                      <div className="mb-3 rounded-[18px] border-2 border-emerald-100 bg-emerald-50/80 p-3 text-right text-xs font-bold leading-6 text-emerald-700">
                        به جای {toPersianNumber(backendPaymentCount)} پرداخت جداگانه، با {toPersianNumber(remainingPaymentCount)} پرداخت حساب گروه صاف می‌شود.
                      </div>
                    ) : null}

                    {settlementSaving ? (
                      <div className="mb-3 flex items-center justify-center gap-2 rounded-[20px] border-2 border-orange-100 bg-white p-4 text-center text-sm font-bold text-orange-700">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        در حال بروزرسانی تسویه...
                      </div>
                    ) : null}

                    {optimizedSettlements.length === 0 ? (
                      <div className="rounded-[20px] border-2 border-dashed border-orange-200 bg-white p-6 text-center text-sm font-semibold text-muted shadow-sm">
                        فعلاً پرداختی لازم نیست؛ حساب اعضای گروه تسویه است.
                      </div>
                    ) : null}

                    <div className="space-y-3">
                      {optimizedSettlements.map((item) => {
                        const isPayer = item.payer_user_id === currentUserId;
                        const isReceiver = item.receiver_user_id === currentUserId;

                        return (
                          <ListRow key={item.id} tone="slate">
                            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                              <div className="text-right">
                                <div className="text-sm font-black text-text">
                                  {item.payerName} به {item.receiverName}
                                </div>

                                <div className="mt-1 text-base font-black text-orange-700">
                                  {formatMoney(item.amount_minor)}
                                </div>

                                <div className="mt-1 text-xs font-bold text-muted">
                                  همین یک پرداخت، سهم نهایی این دو نفر را صاف می‌کند.
                                </div>
                              </div>

                              <div className="flex flex-wrap items-center gap-2 sm:justify-end">
                                {isPayer ? (
                                  <button
                                    type="button"
                                    onClick={() => handleCreateManualSettlement(item.receiver_user_id, item.amount_minor)}
                                    disabled={settlementSaving}
                                    className="h-9 rounded-[13px] border-2 border-emerald-100 bg-emerald-50 px-3 text-xs font-black text-emerald-700 disabled:opacity-60"
                                  >
                                    ثبت همین پرداخت
                                  </button>
                                ) : null}

                                {isReceiver ? (
                                  <span className="rounded-[13px] border-2 border-sky-100 bg-sky-50 px-3 py-2 text-xs font-black text-sky-700">
                                    منتظر پرداخت
                                  </span>
                                ) : null}

                                {!isPayer && !isReceiver ? (
                                  <span className="rounded-[13px] border-2 border-slate-100 bg-white px-3 py-2 text-xs font-black text-slate-500">
                                    پرداخت بین اعضای دیگر
                                  </span>
                                ) : null}
                              </div>
                            </div>
                          </ListRow>
                        );
                      })}
                    </div>
                  </div>



                  {balances.length > 0 ? (
                    <FieldSurface>
                      <h3 className="mb-3 text-right text-base font-black text-text">
                        حساب اعضا
                      </h3>

                      <div className="space-y-2">
                        {balances.map((balance) => {
                          const amount = balance.net_balance_minor || 0;

                          return (
                            <div
                              key={balance.user_id}
                              className="flex items-center justify-between rounded-[18px] border-2 border-slate-100 bg-white/86 px-3 py-3 text-sm font-bold shadow-sm"
                            >
                              <span className="text-text">
                                {getBalanceDisplayName(balance, members)}
                              </span>

                              <span
                                className={
                                  amount < 0
                                    ? 'text-rose-600'
                                    : amount > 0
                                      ? 'text-emerald-600'
                                      : 'text-slate-600'
                                }
                              >
                                {formatSignedMoney(amount)}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </FieldSurface>
                  ) : null}

                  {settlements.length > 0 ? (
                    <FieldSurface>
                      <h3 className="mb-3 text-right text-base font-black text-text">
                        پرداخت‌های ثبت‌شده
                      </h3>

                      <div className="space-y-3">
                        {settlements.slice(0, 5).map((settlement) => {
                          const isPayer = settlement.payer_user_id === currentUserId;
                          const isReceiver = settlement.receiver_user_id === currentUserId;

                          return (
                            <ListRow key={settlement.id} tone="slate">
                              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                                <div className="text-right">
                                  <div className="text-sm font-black text-text">
                                    {getUserDisplayFromId(settlement.payer_user_id, members)} به{' '}
                                    {getUserDisplayFromId(settlement.receiver_user_id, members)}
                                  </div>

                                  <div className="mt-1 text-xs font-bold text-muted">
                                    {getSettlementStatusLabel(settlement.status)} •{' '}
                                    {toPersianDate(settlement.created_at)}
                                  </div>
                                </div>

                                <div className="flex flex-wrap items-center gap-2 sm:justify-end">
                                  <span className="rounded-[14px] border-2 border-slate-100 bg-white px-3 py-2 text-sm font-black text-slate-700 shadow-sm">
                                    {formatMoney(settlement.amount_minor)}
                                  </span>

                                  {isReceiver && settlement.status === 'PENDING_CONFIRMATION' ? (
                                    <>
                                      <button
                                        type="button"
                                        onClick={() => handleSettlementAction(settlement, 'confirm')}
                                        disabled={settlementSaving}
                                        className="h-9 rounded-[13px] border-2 border-emerald-100 bg-emerald-50 px-3 text-xs font-black text-emerald-700 disabled:opacity-60"
                                      >
                                        گرفتم
                                      </button>

                                      <button
                                        type="button"
                                        onClick={() => handleSettlementAction(settlement, 'reject')}
                                        disabled={settlementSaving}
                                        className="h-9 rounded-[13px] border-2 border-rose-100 bg-rose-50 px-3 text-xs font-black text-rose-600 disabled:opacity-60"
                                      >
                                        نگرفتم
                                      </button>
                                    </>
                                  ) : null}

                                  {isPayer && settlement.status === 'PENDING_CONFIRMATION' ? (
                                    <button
                                      type="button"
                                      onClick={() => handleSettlementAction(settlement, 'cancel')}
                                      disabled={settlementSaving}
                                      className="h-9 rounded-[13px] border-2 border-slate-200 bg-slate-100 px-3 text-xs font-black text-slate-700 disabled:opacity-60"
                                    >
                                      لغو
                                    </button>
                                  ) : null}
                                </div>
                              </div>
                            </ListRow>
                          );
                        })}
                      </div>
                    </FieldSurface>
                  ) : null}
                </div>
              )}
            </SectionCard>

            <SectionCard
              id="settings-card"
              title="تنظیمات گروه"
              icon={<Settings className="h-5 w-5" />}
              accent="slate"
            >
              <FieldSurface>
                <div className="space-y-4">
                  <label className="block text-right">
                    <span className="mb-2 block text-sm font-black text-text">
                      عنوان گروه
                    </span>

                    <input
                      dir="rtl"
                      value={title}
                      onChange={(event) => setTitle(event.target.value)}
                      className="h-12 w-full rounded-[18px] border-2 border-slate-200 bg-white/80 px-4 text-sm font-bold text-text outline-none transition focus:border-emerald-300 focus:bg-white focus:ring-4 focus:ring-emerald-500/10"
                    />
                  </label>

                  <label className="block text-right">
                    <span className="mb-2 block text-sm font-black text-text">
                      نوع گروه
                    </span>

                    <select
                      value={groupType}
                      onChange={(event) => setGroupType(event.target.value as BackendGroupType)}
                      className="h-12 w-full rounded-[18px] border-2 border-slate-200 bg-white/80 px-4 text-sm font-bold text-text outline-none transition focus:border-emerald-300 focus:bg-white focus:ring-4 focus:ring-emerald-500/10"
                    >
                      <option value="GENERAL">عمومی</option>
                      <option value="EVENT">رویداد</option>
                    </select>
                  </label>

                  <label className="block text-right">
                    <span className="mb-2 block text-sm font-black text-text">
                      توضیحات
                    </span>

                    <textarea
                      dir="rtl"
                      value={description}
                      onChange={(event) => setDescription(event.target.value)}
                      className="min-h-[110px] w-full resize-none rounded-[18px] border-2 border-slate-200 bg-white/80 px-4 py-3 text-sm font-semibold leading-7 text-text outline-none transition focus:border-emerald-300 focus:bg-white focus:ring-4 focus:ring-emerald-500/10"
                    />
                  </label>

                  <ActionButton
                    onClick={handleSave}
                    disabled={saving || !canManageGroup}
                    className="h-12 w-full"
                  >
                    {saving ? (
                      <InlineLoader label="در حال ذخیره..." />
                    ) : (
                      <>
                        <Save className="h-4 w-4" />
                        ذخیره تغییرات
                      </>
                    )}
                  </ActionButton>

                  {!canManageGroup ? (
                    <p className="text-center text-xs font-bold text-amber-700">
                      فقط مدیر یا مالک گروه می‌تواند تنظیمات را ویرایش کند.
                    </p>
                  ) : null}
                </div>
              </FieldSurface>
            </SectionCard>
          </section>

          <aside className="space-y-5">
            <SectionCard
              id="members-card"
              title="اعضای گروه"
              icon={<Users className="h-5 w-5" />}
              accent="sky"
            >
              <div className="rounded-[24px] border-2 border-emerald-200/80 bg-gradient-to-l from-white via-emerald-50/80 to-emerald-50/50 p-4 text-right shadow-[inset_3px_0_0_#10B981,0_16px_38px_rgba(16,185,129,0.045)]">
                <div className="mb-3 flex items-start justify-between gap-3">
                  <h3 className="text-base font-black text-emerald-700">
                    دعوت عضو جدید
                  </h3>

                  <Link2 className="h-5 w-5 text-emerald-600" />
                </div>

                {!invite ? (
                  <ActionButton
                    onClick={handleCreateInvite}
                    disabled={inviteLoading || !canManageGroup}
                    className="w-full"
                  >
                    <Link2 className="h-4 w-4" />
                    {inviteLoading ? 'در حال ساخت...' : 'ساخت لینک دعوت'}
                  </ActionButton>
                ) : (
                  <div className="space-y-3">
                    <input
                      readOnly
                      dir="ltr"
                      value={inviteUrl || 'لینکی برای نمایش آماده نیست'}
                      className="h-11 w-full rounded-[16px] border-2 border-emerald-100 bg-white px-3 text-left text-xs font-semibold text-slate-700 outline-none shadow-sm"
                    />

                    <div className="grid grid-cols-2 gap-2">
                      <button
                        type="button"
                        onClick={handleCopyInvite}
                        disabled={!inviteUrl}
                        className="inline-flex h-10 items-center justify-center gap-2 rounded-[15px] bg-white px-3 text-xs font-black text-emerald-700 shadow-sm transition hover:bg-emerald-50 disabled:opacity-60"
                      >
                        <Copy className="h-4 w-4" />
                        {copied ? 'کپی شد' : 'کپی'}
                      </button>

                      <button
                        type="button"
                        onClick={handleRevokeInvite}
                        className="inline-flex h-10 items-center justify-center gap-2 rounded-[15px] bg-rose-50 px-3 text-xs font-black text-rose-600 transition hover:bg-rose-100"
                      >
                        <Trash2 className="h-4 w-4" />
                        لغو
                      </button>
                    </div>

                    {invite.expires_at ? (
                      <p className="text-center text-xs font-bold text-emerald-700/75">
                        اعتبار تا: {toPersianDate(invite.expires_at)}
                      </p>
                    ) : null}
                  </div>
                )}

                {!canManageGroup ? (
                  <p className="mt-3 text-center text-xs font-bold text-amber-700">
                    فقط مدیر یا مالک گروه می‌تواند لینک دعوت بسازد.
                  </p>
                ) : null}
              </div>

              <div className="mt-4 space-y-3">
                {membersLoading ? (
                  <div className="flex items-center justify-center gap-2 rounded-[22px] border-2 border-sky-100 bg-sky-50 p-5 text-center text-sm font-bold text-sky-700">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    در حال دریافت اعضا...
                  </div>
                ) : null}

                {!membersLoading && members.length === 0 ? (
                  <EmptyState
                    title="هنوز عضوی برای نمایش نیست"
                    description="بعد از دعوت عضوها، لیست اینجا نمایش داده می‌شود."
                  />
                ) : null}

                {members.map((member) => {
                  const memberId = getMemberId(member);
                  const userId = getMemberUserId(member);
                  const isSelf = userId === currentUserId;
                  const canRemoveMember = canManageGroup && !isSelf && member.role !== 'OWNER';

                  return (
                    <ListRow key={memberId || userId}>
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <div className="flex min-w-0 items-center gap-3">
                          <MemberAvatar name={getMemberName(member)} />

                          <div className="min-w-0 text-right">
                            <div className="truncate text-sm font-black text-text">
                              {getMemberName(member)} {isSelf ? '(شما)' : ''}
                            </div>

                            <div className="mt-1 truncate text-xs font-semibold text-muted">
                              {getMemberPhone(member)}
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center justify-between gap-2 sm:justify-end">
                          <span className="inline-flex items-center gap-1.5 rounded-full border-2 border-emerald-100 bg-emerald-50 px-3 py-1.5 text-xs font-black text-emerald-700">
                            <Crown className="h-3.5 w-3.5" />
                            {getRoleLabel(member.role)}
                          </span>

                          {canRemoveMember ? (
                            <button
                              type="button"
                              onClick={() => handleRemoveMember(member)}
                              className="inline-flex h-9 items-center justify-center gap-1.5 rounded-[13px] border-2 border-rose-100 bg-rose-50 px-3 text-xs font-black text-rose-600 transition hover:bg-rose-100"
                            >
                              <UserMinus className="h-3.5 w-3.5" />
                              حذف
                            </button>
                          ) : null}
                        </div>
                      </div>
                    </ListRow>
                  );
                })}
              </div>
            </SectionCard>
          </aside>
        </div>
      </div>
    </main>
  );
}