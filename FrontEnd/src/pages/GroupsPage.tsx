import {
  AlertCircle,
  Archive,
  CheckCircle2,
  ChevronLeft,
  HandCoins,
  Link2,
  Loader2,
  Plus,
  RefreshCw,
  Search,
  Users,
  X,
} from 'lucide-react';
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { GroupCard } from '../components/GroupCard';
import { extractInviteToken } from '../lib/groupApi';
import { MoneyWithWords, normalizeMoneyAmount } from '../lib/money';
import type { Group, GroupStatus } from '../types';

type GroupFilter = 'ACTIVE' | 'ARCHIVED';

export interface GroupBalanceSummary {
  groupId: string;
  groupName: string;
  status?: GroupStatus;
  paidMinor: number;
  shareMinor: number;
  netMinor: number;
}

interface GroupsPageProps {
  groups: Group[];
  groupBalances?: GroupBalanceSummary[];
  balancesLoading?: boolean;
  loading?: boolean;
  error?: string | null;
  onCreateGroup: () => void;
  onOpenGroup: (groupId: string) => void;
  onOpenInvite: (tokenOrLink: string) => void;
  onDeleteGroup: (group: Group) => void;
  onRetry?: () => void;
}

function toPersianNumber(value: string | number) {
  return String(value).replace(/\d/g, (digit) => '۰۱۲۳۴۵۶۷۸۹'[Number(digit)]);
}

function formatMoney(minor = 0) {
  return `تومان \u2066${toPersianNumber(Math.abs(Math.round(minor)).toLocaleString('en-US'))}\u2069`;
}

function getSignedMoneyLabel(minor = 0) {
  return formatMoney(Math.abs(minor));
}

function normalizeSearchText(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[يى]/g, 'ی')
    .replace(/ك/g, 'ک')
    .replace(/[\u200c\u200d]/g, ' ')
    .replace(/\s+/g, ' ');
}

function getGroupSearchText(group: Group) {
  const searchText = [
    group.name,
    group.description,
    group.membersLabel,
    group.statusLabel,
    group.role,
  ]
    .filter(Boolean)
    .join(' ');

  return normalizeSearchText(searchText);
}

function getGroupSortWeight(group: Group) {
  if (group.status === 'ARCHIVED') return 4;

  const amount = normalizeMoneyAmount(group.amount);

  if (amount === 0) return 3;
  if (group.tone === 'negative') return 1;
  if (group.tone === 'positive') return 2;

  return 3;
}

function sortGroupsByNeed(groups: Group[]) {
  return [...groups].sort((first, second) => {
    const weightDiff = getGroupSortWeight(first) - getGroupSortWeight(second);

    if (weightDiff !== 0) return weightDiff;

    return Math.abs(normalizeMoneyAmount(second.amount)) - Math.abs(normalizeMoneyAmount(first.amount));
  });
}

function JoinInviteModal({
  open,
  onClose,
  onOpenInvite,
}: {
  open: boolean;
  onClose: () => void;
  onOpenInvite: (tokenOrLink: string) => void;
}) {
  const [inviteValue, setInviteValue] = useState('');
  const dialogRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const token = extractInviteToken(inviteValue);
  const showInvalidInvite = Boolean(inviteValue.trim()) && !token;

  useEffect(() => {
    if (!open) return;

    const previouslyFocused = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    const focusInputFrame = window.requestAnimationFrame(() => inputRef.current?.focus());
    document.body.style.overflow = 'hidden';

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
        return;
      }

      if (event.key !== 'Tab' || !dialogRef.current) return;

      const focusableElements = Array.from(
        dialogRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      );
      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      if (!firstElement || !lastElement) return;

      if (event.shiftKey && document.activeElement === firstElement) {
        event.preventDefault();
        lastElement.focus();
      } else if (!event.shiftKey && document.activeElement === lastElement) {
        event.preventDefault();
        firstElement.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);

    return () => {
      window.cancelAnimationFrame(focusInputFrame);
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = previousOverflow;
      previouslyFocused?.focus();
    };
  }, [onClose, open]);

  if (!open) return null;

  const handleSubmit = () => {
    if (!token) return;

    onOpenInvite(token);
    setInviteValue('');
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 px-4 py-6 backdrop-blur-sm"
      dir="rtl"
      role="dialog"
      aria-modal="true"
      aria-labelledby="join-invite-title"
      aria-describedby="join-invite-description"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <div
        ref={dialogRef}
        className="w-full max-w-[460px] overflow-hidden rounded-[28px] border border-white/70 bg-white shadow-[0_30px_90px_rgba(15,23,42,0.28)]"
      >
        <div className="relative overflow-hidden bg-gradient-to-l from-emerald-50 via-white to-slate-50 p-5 sm:p-6">
          <button
            type="button"
            onClick={onClose}
            className="absolute left-4 top-4 flex h-10 w-10 items-center justify-center rounded-[16px] border border-slate-100 bg-white text-slate-500 shadow-sm transition hover:border-rose-100 hover:bg-rose-50 hover:text-rose-500"
            aria-label="بستن"
          >
            <X className="h-5 w-5" />
          </button>

          <div className="flex items-start gap-4 pl-12">
            <div className="flex h-13 w-13 shrink-0 items-center justify-center rounded-[22px] border border-emerald-100 bg-emerald-50 text-emerald-600 shadow-sm">
              <Link2 className="h-6 w-6" />
            </div>

            <div className="min-w-0 text-right">
              <h2 id="join-invite-title" className="text-xl font-extrabold text-text">
                پیوستن به گروه
              </h2>
              <p
                id="join-invite-description"
                className="mt-2 text-sm font-semibold leading-7 text-muted"
              >
                لینک یا کد دعوتی که دریافت کرده‌اید را وارد کنید.
              </p>
            </div>
          </div>
        </div>

        <div className="p-5 sm:p-6">
          <label className="block text-right">
            <span className="mb-2 block text-xs font-extrabold text-slate-600">
              لینک یا کد دعوت
            </span>

            <div className="relative">
              <Link2 className="pointer-events-none absolute right-4 top-1/2 h-4 w-4 -translate-y-1/2 text-emerald-600" />

              <input
                ref={inputRef}
                dir="ltr"
                value={inviteValue}
                onChange={(event) => setInviteValue(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    handleSubmit();
                  }
                }}
                aria-invalid={showInvalidInvite}
                aria-describedby={showInvalidInvite ? 'invite-link-error' : undefined}
                placeholder="لینک یا کد دعوت را وارد کنید"
                className="h-13 w-full rounded-[20px] border-2 border-slate-200 bg-slate-50/80 pr-11 pl-4 text-left text-sm font-semibold text-slate-700 outline-none transition placeholder:text-right placeholder:text-slate-400 focus:border-emerald-300 focus:bg-white focus:ring-4 focus:ring-emerald-500/10"
              />
            </div>

            {showInvalidInvite ? (
              <span
                id="invite-link-error"
                className="mt-2 block text-xs font-bold text-rose-600"
              >
                لینک یا کد دعوت معتبر نیست؛ دوباره بررسی کنید.
              </span>
            ) : null}
          </label>

          <div className="mt-5 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
            <button
              type="button"
              onClick={onClose}
              className="inline-flex h-12 items-center justify-center rounded-[18px] border border-slate-200 bg-white px-5 text-sm font-extrabold text-slate-600 transition hover:bg-slate-50"
            >
              انصراف
            </button>

            <button
              type="button"
              onClick={handleSubmit}
              disabled={!token}
              className="inline-flex h-12 items-center justify-center gap-2 rounded-[18px] bg-gradient-to-l from-[#00915F] to-[#00A86B] px-6 text-sm font-extrabold text-white shadow-[0_14px_30px_rgba(0,168,107,0.22)] transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-45 disabled:hover:translate-y-0"
            >
              بررسی دعوت
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function GroupDebtsSummaryCard({
  summaries,
  loading,
  onOpenGroup,
  showPriorityItems = true,
}: {
  summaries: GroupBalanceSummary[];
  loading: boolean;
  onOpenGroup: (groupId: string) => void;
  showPriorityItems?: boolean;
}) {
  const activeSummaries = summaries.filter((item) => item.status !== 'ARCHIVED');
  const debtItems = activeSummaries.filter((item) => item.netMinor < 0);
  const creditItems = activeSummaries.filter((item) => item.netMinor > 0);
  const totalDebtMinor = debtItems.reduce((sum, item) => sum + Math.abs(item.netMinor), 0);
  const totalCreditMinor = creditItems.reduce((sum, item) => sum + item.netMinor, 0);
  const priorityItems = activeSummaries
    .filter((item) => item.netMinor !== 0)
    .sort((first, second) => {
      const firstWeight = first.netMinor < 0 ? 0 : 1;
      const secondWeight = second.netMinor < 0 ? 0 : 1;

      if (firstWeight !== secondWeight) return firstWeight - secondWeight;

      return Math.abs(second.netMinor) - Math.abs(first.netMinor);
    })
    .slice(0, 3);

  return (
    <div className="groups-panel rounded-3xl border p-5">
      <div className="mb-5 flex items-center justify-between gap-3">
        <div className="text-right">
          <h2 className="text-lg font-extrabold text-text">وضعیت مالی شما</h2>
          <p className="mt-1 text-xs font-semibold leading-6 text-muted">
            خلاصه‌ی بدهی و طلب در گروه‌های فعال
          </p>
        </div>

        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[18px] bg-emerald-50 text-emerald-600">
          <HandCoins className="h-5 w-5" />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="groups-summary-mini groups-summary-mini--debt rounded-[20px] border px-4 py-3 text-right">
          <div className="text-xs font-extrabold text-rose-500">باید پرداخت کنید</div>
          {loading ? (
            <div className="mt-3 h-5 w-20 animate-pulse rounded-full bg-rose-200/70" />
          ) : (
            <MoneyWithWords
              amount={totalDebtMinor}
              className="mt-1"
              valueClassName="text-base font-extrabold text-rose-600"
              showText={false}
            />
          )}
        </div>

        <div className="groups-summary-mini groups-summary-mini--credit rounded-[20px] border px-4 py-3 text-right">
          <div className="text-xs font-extrabold text-emerald-600">باید دریافت کنید</div>
          {loading ? (
            <div className="mt-3 h-5 w-20 animate-pulse rounded-full bg-emerald-200/70" />
          ) : (
            <MoneyWithWords
              amount={totalCreditMinor}
              className="mt-1"
              valueClassName="text-base font-extrabold text-emerald-700"
              showText={false}
            />
          )}
        </div>
      </div>

      {loading ? (
        <div className="groups-inline-state mt-4 flex items-center justify-center gap-2 rounded-[20px] border p-4 text-center text-sm font-semibold text-muted">
          <Loader2 className="h-4 w-4 animate-spin" />
          در حال محاسبه...
        </div>
      ) : null}

      {!loading && activeSummaries.length === 0 ? (
        <div className="groups-inline-state mt-4 rounded-[20px] border border-dashed p-5 text-center text-sm font-semibold leading-7 text-muted">
          هنوز هزینه‌ای برای محاسبه حساب گروه‌ها ثبت نشده.
        </div>
      ) : null}

      {!loading && activeSummaries.length > 0 && priorityItems.length === 0 ? (
        <div className="groups-inline-state mt-4 flex items-center justify-center gap-2 rounded-[20px] border p-4 text-sm font-extrabold text-emerald-700">
          <CheckCircle2 className="h-4 w-4" />
          همه‌ی گروه‌های فعال تسویه‌اند
        </div>
      ) : null}

      {!loading && showPriorityItems && priorityItems.length > 0 ? (
        <div className="mt-4">
          <div className="mb-2 px-1 text-xs font-extrabold text-muted">
            گروه‌های نیازمند توجه
          </div>

          <div className="space-y-2">
            {priorityItems.map((summary) => {
          const isDebt = summary.netMinor < 0;
          const isCredit = summary.netMinor > 0;

          return (
            <button
              key={summary.groupId}
              type="button"
              onClick={() => onOpenGroup(summary.groupId)}
              className="groups-summary-row flex w-full items-center justify-between gap-3 rounded-[20px] border px-4 py-3 text-right transition"
            >
              <div className="flex min-w-0 items-center gap-2">
                <ChevronLeft className="h-4 w-4 shrink-0 text-slate-400" />
                <div className="min-w-0">
                <div className="truncate text-sm font-extrabold text-text">
                  {summary.groupName}
                </div>
                <div className="mt-1 text-xs font-semibold text-muted">
                  {isDebt
                    ? 'بدهی برای پرداخت داری'
                    : isCredit
                      ? 'در این گروه طلبکاری'
                      : 'این گروه تسویه است'}
                </div>
                </div>
              </div>

              <div className="shrink-0 text-left">
                <div
                  className={[
                    'text-sm font-extrabold',
                    isDebt
                      ? 'text-rose-600'
                      : isCredit
                        ? 'text-emerald-600'
                        : 'text-slate-500',
                  ].join(' ')}
                >
                  {getSignedMoneyLabel(summary.netMinor)}
                </div>
                <div className="mt-1 text-xs font-semibold text-muted">
                  {isDebt ? 'بدهکار' : isCredit ? 'طلبکار' : 'تسویه'}
                </div>
              </div>
            </button>
          );
            })}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function FilterButton({
  active,
  icon,
  label,
  count,
  onClick,
}: {
  active: boolean;
  icon: ReactNode;
  label: string;
  count: number;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={[
        'groups-filter-button inline-flex h-11 flex-1 items-center justify-center gap-2 rounded-[18px] border px-4 text-sm font-extrabold transition sm:flex-none',
        active
          ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
          : 'border-slate-200 bg-white text-slate-600 hover:border-emerald-200 hover:bg-emerald-50 hover:text-emerald-700',
      ].join(' ')}
    >
      {icon}
      {label}
      <span
        className={[
          'rounded-full px-2 py-0.5 text-xs font-extrabold',
          active ? 'bg-white text-emerald-700' : 'bg-slate-100 text-slate-500',
        ].join(' ')}
      >
        {toPersianNumber(count)}
      </span>
    </button>
  );
}

function LoadingState() {
  return (
    <>
      <div className="groups-list-skeleton overflow-hidden rounded-3xl border lg:hidden">
        {Array.from({ length: 4 }).map((_, index) => (
          <div
            key={index}
            className={[
              'flex min-h-[82px] animate-pulse items-center gap-3 px-3 py-2',
              index < 3 ? 'border-b border-slate-100' : '',
            ].join(' ')}
          >
            <div className="h-[52px] w-[52px] shrink-0 rounded-full bg-slate-100" />
            <div className="min-w-0 flex-1 space-y-2">
              <div className="h-4 w-28 rounded-full bg-slate-100" />
              <div className="h-3 w-20 rounded-full bg-slate-100" />
            </div>
            <div className="h-3 w-16 rounded-full bg-slate-100" />
          </div>
        ))}
      </div>

      <div className="hidden gap-4 lg:grid lg:grid-cols-2 2xl:grid-cols-3">
        {Array.from({ length: 4 }).map((_, index) => (
          <div
            key={index}
            className="groups-panel min-h-[212px] animate-pulse rounded-3xl border p-5"
          >
            <div className="mb-6 flex items-center justify-between">
              <div className="space-y-3">
                <div className="h-4 w-24 rounded-full bg-slate-100" />
                <div className="h-6 w-36 rounded-full bg-slate-100" />
                <div className="h-4 w-28 rounded-full bg-slate-100" />
              </div>
              <div className="h-[74px] w-[74px] rounded-[26px] bg-slate-100" />
            </div>
            <div className="mt-12 h-16 rounded-[20px] bg-slate-100" />
            <div className="mt-4 h-11 rounded-[17px] bg-slate-100" />
          </div>
        ))}
      </div>
    </>
  );
}

function EmptyGroupsState({
  filter,
  hasSearch,
  onResetSearch,
}: {
  filter: GroupFilter;
  hasSearch: boolean;
  onResetSearch: () => void;
}) {
  const archived = filter === 'ARCHIVED';

  return (
    <div className="groups-empty-state rounded-3xl border border-dashed p-8 text-center sm:p-10">
      <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-[24px] bg-white text-emerald-600 shadow-sm">
        {hasSearch ? (
          <Search className="h-7 w-7" />
        ) : archived ? (
          <Archive className="h-7 w-7" />
        ) : (
          <Users className="h-7 w-7" />
        )}
      </div>

      <h2 className="text-xl font-extrabold text-text">
        {hasSearch
          ? 'گروهی با این جستجو پیدا نشد'
          : archived
            ? 'گروه آرشیوشده‌ای نداری'
            : 'هنوز گروه فعالی نداری'}
      </h2>

      <p className="mx-auto mt-2 max-w-[480px] text-sm font-semibold leading-7 text-muted">
        {hasSearch
          ? 'عبارت جستجو را ساده‌تر کن یا جستجو را پاک کن.'
          : archived
            ? 'وقتی گروهی را آرشیو کنی، اینجا نمایش داده می‌شود.'
            : 'اولین گروهت را بساز تا هزینه‌ها و اعضا را راحت مدیریت کنی.'}
      </p>

      {hasSearch ? (
        <div className="mt-5 flex flex-col justify-center gap-3 sm:flex-row">
          <button
            type="button"
            onClick={onResetSearch}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-[17px] border border-slate-200 bg-white px-5 text-sm font-extrabold text-slate-700 transition hover:bg-slate-50"
          >
            <X className="h-4 w-4" />
            پاک کردن جستجو
          </button>
        </div>
      ) : null}
    </div>
  );
}

export function GroupsPage({
  groups,
  groupBalances = [],
  balancesLoading = false,
  loading = false,
  error = null,
  onCreateGroup,
  onOpenGroup,
  onOpenInvite,
  onDeleteGroup,
  onRetry,
}: GroupsPageProps) {
  const [filter, setFilter] = useState<GroupFilter>('ACTIVE');
  const [searchTerm, setSearchTerm] = useState('');
  const [mobileSearchOpen, setMobileSearchOpen] = useState(false);
  const [inviteModalOpen, setInviteModalOpen] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const listControlsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!mobileSearchOpen) return;

    const focusFrame = window.requestAnimationFrame(() => searchInputRef.current?.focus());

    return () => window.cancelAnimationFrame(focusFrame);
  }, [mobileSearchOpen]);

  const { activeGroups, archivedGroups } = useMemo(
    () => ({
      activeGroups: groups.filter((group) => group.status !== 'ARCHIVED'),
      archivedGroups: groups.filter((group) => group.status === 'ARCHIVED'),
    }),
    [groups],
  );
  const activeCount = activeGroups.length;
  const archivedCount = archivedGroups.length;

  const visibleGroups = useMemo(() => {
    const filteredByStatus = filter === 'ARCHIVED' ? archivedGroups : activeGroups;
    const normalizedSearch = normalizeSearchText(searchTerm);
    const searchResults = normalizedSearch
      ? filteredByStatus.filter((group) =>
          getGroupSearchText(group).includes(normalizedSearch),
        )
      : filteredByStatus;

    return sortGroupsByNeed(searchResults);
  }, [activeGroups, archivedGroups, filter, searchTerm]);

  const hasSearch = Boolean(searchTerm.trim());
  const hasAnyGroup = groups.length > 0;
  const showBalanceSummary = !loading && !error && activeCount > 0;
  const currentGroupCount = filter === 'ACTIVE' ? activeCount : archivedCount;
  const showSearchControl = currentGroupCount >= 5 || hasSearch || mobileSearchOpen;

  const clearSearch = () => {
    setSearchTerm('');
    setMobileSearchOpen(false);
  };

  const toggleMobileArchive = () => {
    setFilter((currentFilter) => (currentFilter === 'ACTIVE' ? 'ARCHIVED' : 'ACTIVE'));
    clearSearch();

    window.requestAnimationFrame(() => {
      const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      listControlsRef.current?.scrollIntoView({
        behavior: reduceMotion ? 'auto' : 'smooth',
        block: 'start',
      });
    });
  };

  return (
    <>
      <main
        className={[
          'app-page groups-page lg:min-h-[calc(100vh-94px)]',
          showBalanceSummary ? 'xl:grid xl:grid-cols-[minmax(0,1fr)_370px]' : '',
        ].join(' ')}
      >
        <section className="min-w-0">
          <div className="app-container space-y-4">
            <div ref={listControlsRef} className="groups-list-controls scroll-mt-4 rounded-3xl border p-3">
              <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
                <div className="flex items-center justify-between gap-3 px-1">
                  <div className="text-right">
                    <h1 className="text-lg font-extrabold text-text">
                      گروه‌ها
                    </h1>
                    <p className="mt-1 text-xs font-bold text-muted">
                      {loading ? 'در حال دریافت گروه‌ها...' : `${toPersianNumber(currentGroupCount)} گروه`}
                    </p>
                  </div>

                  {!loading && !error && showSearchControl ? (
                    <button
                      type="button"
                      onClick={() => {
                        if (mobileSearchOpen || hasSearch) {
                          clearSearch();
                        } else {
                          setMobileSearchOpen(true);
                        }
                      }}
                      className="groups-search-toggle flex h-11 w-11 items-center justify-center rounded-2xl border text-slate-600 lg:hidden"
                      aria-label={mobileSearchOpen || hasSearch ? 'بستن جستجو' : 'جستجوی گروه'}
                      aria-expanded={mobileSearchOpen || hasSearch}
                      aria-controls="groups-search-box"
                    >
                      {mobileSearchOpen || hasSearch ? (
                        <X className="h-5 w-5" />
                      ) : (
                        <Search className="h-5 w-5" />
                      )}
                    </button>
                  ) : null}
                </div>

                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:flex lg:w-auto">
                  <button
                    type="button"
                    onClick={onCreateGroup}
                    className="inline-flex h-12 w-full items-center justify-center gap-2 rounded-[18px] bg-gradient-to-l from-[#00915F] to-[#00A86B] px-5 text-sm font-extrabold text-white shadow-[0_12px_26px_rgba(0,168,107,0.18)] transition hover:-translate-y-0.5 lg:w-auto"
                  >
                    <Plus className="h-5 w-5" />
                    ساخت گروه جدید
                  </button>

                  <button
                    type="button"
                    onClick={() => setInviteModalOpen(true)}
                    className="groups-secondary-action inline-flex h-12 w-full items-center justify-center gap-2 rounded-[18px] border px-5 text-sm font-extrabold transition hover:-translate-y-0.5 lg:w-auto"
                  >
                    <Link2 className="h-5 w-5" />
                    پیوستن با لینک دعوت
                  </button>
                </div>
              </div>

              {!loading && !error && hasAnyGroup ? (
                <div
                  className={[
                    'gap-2 lg:grid-cols-[auto_minmax(260px,1fr)] lg:items-center',
                    mobileSearchOpen || hasSearch
                      ? 'mt-3 grid'
                      : 'hidden lg:mt-3 lg:grid',
                  ].join(' ')}
                >
                  <div className="hidden grid-cols-2 gap-2 lg:flex lg:flex-wrap">
                    <FilterButton
                      active={filter === 'ACTIVE'}
                      icon={<CheckCircle2 className="h-4 w-4" />}
                      label="فعال"
                      count={activeCount}
                      onClick={() => {
                        setFilter('ACTIVE');
                        clearSearch();
                      }}
                    />

                    <FilterButton
                      active={filter === 'ARCHIVED'}
                      icon={<Archive className="h-4 w-4" />}
                      label="آرشیو"
                      count={archivedCount}
                      onClick={() => {
                        setFilter('ARCHIVED');
                        clearSearch();
                      }}
                    />
                  </div>

                  {showSearchControl ? (
                    <div
                      id="groups-search-box"
                      className={[
                        'relative',
                        mobileSearchOpen || hasSearch ? 'block' : 'hidden lg:block',
                      ].join(' ')}
                    >
                  <Search className="pointer-events-none absolute right-4 top-1/2 h-4 w-4 -translate-y-1/2 text-emerald-600" />

                  <label htmlFor="groups-search" className="sr-only">
                    جستجو در گروه‌ها
                  </label>
                  <input
                    ref={searchInputRef}
                    id="groups-search"
                    type="search"
                    dir="rtl"
                    autoComplete="off"
                    value={searchTerm}
                    onChange={(event) => setSearchTerm(event.target.value)}
                    placeholder="جستجوی گروه؛ مثلاً سفر، خانه، شام..."
                    className="groups-search-input h-12 w-full rounded-[18px] border pr-11 pl-11 text-sm font-bold text-text outline-none transition placeholder:font-semibold placeholder:text-slate-400 focus:border-emerald-300 focus:ring-4 focus:ring-emerald-500/10"
                  />

                  {hasSearch ? (
                    <button
                      type="button"
                      onClick={clearSearch}
                      className="absolute left-3 top-1/2 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded-full border border-slate-100 bg-white text-slate-500 shadow-sm transition hover:border-rose-100 hover:bg-rose-50 hover:text-rose-500"
                      aria-label="پاک کردن جستجو"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  ) : null}
                    </div>
                  ) : null}
                </div>
              ) : null}

              {!loading && !error && hasSearch ? (
                  <div
                    className="mt-3 flex flex-wrap items-center justify-between gap-2 px-1 text-xs font-extrabold text-muted"
                    aria-live="polite"
                  >
                    <span>
                      نمایش {toPersianNumber(visibleGroups.length)} گروه از{' '}
                      {toPersianNumber(currentGroupCount)}
                    </span>

                    <button
                      type="button"
                      onClick={clearSearch}
                      className="groups-clear-search inline-flex items-center gap-1 rounded-full px-3 py-1 transition"
                    >
                      <RefreshCw className="h-3.5 w-3.5" />
                      حذف جستجو
                    </button>
                  </div>
                ) : null}

              {error ? (
                <div
                  className="groups-error mt-3 rounded-3xl border p-5 text-center text-sm font-extrabold"
                  role="alert"
                >
                  <AlertCircle className="mx-auto mb-2 h-6 w-6" />
                  <div>{error}</div>
                  {onRetry ? (
                    <button
                      type="button"
                      onClick={onRetry}
                      className="mt-4 inline-flex h-11 items-center justify-center gap-2 rounded-2xl border border-rose-200 bg-white px-5 text-sm font-extrabold text-rose-700 transition hover:bg-rose-50"
                    >
                      <RefreshCw className="h-4 w-4" />
                      تلاش دوباره
                    </button>
                  ) : null}
                </div>
              ) : null}

              {loading ? (
                <div className="mt-3">
                  <LoadingState />
                </div>
              ) : null}

              {!loading && !error && visibleGroups.length === 0 ? (
                <div className="mt-3">
                  <EmptyGroupsState
                    filter={filter}
                    hasSearch={hasSearch}
                    onResetSearch={clearSearch}
                  />
                </div>
              ) : null}

              {!loading && !error && visibleGroups.length > 0 ? (
                  <div
                    className="groups-list-grid mt-3 grid gap-4 lg:grid-cols-2 2xl:grid-cols-3"
                    aria-label="فهرست گروه‌ها"
                  >
                    {visibleGroups.map((group, index) => (
                      <GroupCard
                        key={group.id}
                        group={group}
                        balanceLoading={balancesLoading}
                        isLastMobile={index === visibleGroups.length - 1}
                        onOpen={() => onOpenGroup(String(group.id))}
                        onDelete={onDeleteGroup}
                      />
                    ))}
                  </div>
              ) : null}

              {!loading &&
              !error &&
              hasAnyGroup &&
              !hasSearch &&
              (filter === 'ACTIVE' ? archivedCount : activeCount) > 0 ? (
                <button
                  type="button"
                  onClick={toggleMobileArchive}
                  className="groups-mobile-archive mt-3 flex min-h-11 w-full items-center justify-center gap-2 rounded-2xl px-4 text-sm font-extrabold text-muted transition lg:hidden"
                >
                  <Archive className="h-4 w-4" />
                  {filter === 'ACTIVE' ? 'مشاهده گروه‌های آرشیوشده' : 'بازگشت به گروه‌های فعال'}
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs">
                    {toPersianNumber(filter === 'ACTIVE' ? archivedCount : activeCount)}
                  </span>
                </button>
              ) : null}
            </div>

            {showBalanceSummary ? (
              <div className="xl:hidden">
                <GroupDebtsSummaryCard
                  summaries={groupBalances}
                  loading={balancesLoading}
                  onOpenGroup={onOpenGroup}
                  showPriorityItems={false}
                />
              </div>
            ) : null}
          </div>
        </section>

        {showBalanceSummary ? (
          <aside
            className="hidden xl:block xl:w-[370px]"
            aria-label="خلاصه وضعیت مالی گروه‌ها"
          >
            <div className="sticky top-5 space-y-5">
              <GroupDebtsSummaryCard
                summaries={groupBalances}
                loading={balancesLoading}
                onOpenGroup={onOpenGroup}
              />
            </div>
          </aside>
        ) : null}
      </main>

      <JoinInviteModal
        open={inviteModalOpen}
        onClose={() => setInviteModalOpen(false)}
        onOpenInvite={onOpenInvite}
      />
    </>
  );
}
