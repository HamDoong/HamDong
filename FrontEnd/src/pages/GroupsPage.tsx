import {
  Archive,
  CheckCircle2,
  HandCoins,
  Link2,
  Loader2,
  Plus,
  RefreshCw,
  Search,
  Users,
  X,
} from 'lucide-react';
import { useMemo, useState, type ReactNode } from 'react';
import { GroupCard } from '../components/GroupCard';
import { extractInviteToken } from '../lib/groupApi';
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
}

function toPersianNumber(value: string | number) {
  return String(value).replace(/\d/g, (digit) => '۰۱۲۳۴۵۶۷۸۹'[Number(digit)]);
}

function formatMoney(minor = 0) {
  return `${toPersianNumber(Math.abs(Math.round(minor)).toLocaleString('en-US'))} تومان`;
}

function getSignedMoneyLabel(minor = 0) {
  if (minor > 0) return `+${formatMoney(minor)}`;
  if (minor < 0) return `-${formatMoney(minor)}`;
  return formatMoney(0);
}

function normalizeSearchText(value: string) {
  return value.trim().toLowerCase().replace(/\s+/g, ' ');
}

function getGroupSearchText(group: Group) {
  return [
    group.name,
    group.description,
    group.membersLabel,
    group.statusLabel,
    group.role,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
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
  const token = extractInviteToken(inviteValue);

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
      aria-label="پیوستن با لینک دعوت"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <div className="w-full max-w-[460px] overflow-hidden rounded-[32px] border border-white/70 bg-white shadow-[0_30px_90px_rgba(15,23,42,0.28)]">
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
              <h2 className="text-xl font-extrabold text-text">
                پیوستن با لینک دعوت
              </h2>
              <p className="mt-2 text-sm font-semibold leading-7 text-muted">
                لینک دعوتی که برات فرستاده شده رو اینجا وارد کن تا گروه بررسی بشه.
              </p>
            </div>
          </div>
        </div>

        <div className="p-5 sm:p-6">
          <label className="block text-right">
            <span className="mb-2 block text-xs font-extrabold text-slate-600">
              لینک دعوت
            </span>

            <div className="relative">
              <Link2 className="pointer-events-none absolute right-4 top-1/2 h-4 w-4 -translate-y-1/2 text-emerald-600" />

              <input
                dir="ltr"
                value={inviteValue}
                onChange={(event) => setInviteValue(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    handleSubmit();
                  }
                }}
                autoFocus
                placeholder="Paste invite link here"
                className="h-13 w-full rounded-[20px] border-2 border-slate-200 bg-slate-50/80 pr-11 pl-4 text-left text-sm font-semibold text-slate-700 outline-none transition placeholder:text-slate-400 focus:border-emerald-300 focus:bg-white focus:ring-4 focus:ring-emerald-500/10"
              />
            </div>
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
              بررسی و پیوستن
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
}: {
  summaries: GroupBalanceSummary[];
  loading: boolean;
  onOpenGroup: (groupId: string) => void;
}) {
  const activeSummaries = summaries.filter((item) => item.status !== 'ARCHIVED');
  const debtItems = activeSummaries.filter((item) => item.netMinor < 0);
  const creditItems = activeSummaries.filter((item) => item.netMinor > 0);
  const totalDebtMinor = debtItems.reduce((sum, item) => sum + Math.abs(item.netMinor), 0);
  const totalCreditMinor = creditItems.reduce((sum, item) => sum + item.netMinor, 0);

  return (
    <div className="rounded-[28px] border-2 border-slate-200 bg-white p-5 shadow-[0_18px_46px_rgba(15,23,42,0.075)]">
      <div className="mb-5 flex items-center justify-between gap-3">
        <div className="text-right">
          <h2 className="text-lg font-extrabold text-text">خلاصه حساب گروه‌ها</h2>
          <p className="mt-1 text-xs font-semibold leading-6 text-muted">
            سریع ببین کجا بدهکار یا طلبکار هستی.
          </p>
        </div>

        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[18px] bg-emerald-50 text-emerald-600">
          <HandCoins className="h-5 w-5" />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-[20px] border border-rose-100 bg-rose-50 px-4 py-3 text-right">
          <div className="text-xs font-extrabold text-rose-500">کل بدهی</div>
          <div className="mt-1 text-base font-extrabold text-rose-600">
            {formatMoney(totalDebtMinor)}
          </div>
        </div>

        <div className="rounded-[20px] border border-emerald-100 bg-emerald-50 px-4 py-3 text-right">
          <div className="text-xs font-extrabold text-emerald-600">کل طلب</div>
          <div className="mt-1 text-base font-extrabold text-emerald-700">
            {formatMoney(totalCreditMinor)}
          </div>
        </div>
      </div>

      {loading ? (
        <div className="mt-4 flex items-center justify-center gap-2 rounded-[20px] border border-slate-100 bg-slate-50 p-4 text-center text-sm font-semibold text-muted">
          <Loader2 className="h-4 w-4 animate-spin" />
          در حال محاسبه...
        </div>
      ) : null}

      {!loading && activeSummaries.length === 0 ? (
        <div className="mt-4 rounded-[20px] border border-dashed border-slate-200 p-5 text-center text-sm font-semibold leading-7 text-muted">
          هنوز هزینه‌ای برای محاسبه حساب گروه‌ها ثبت نشده.
        </div>
      ) : null}

      <div className="mt-4 space-y-3">
        {activeSummaries.slice(0, 5).map((summary) => {
          const isDebt = summary.netMinor < 0;
          const isCredit = summary.netMinor > 0;

          return (
            <button
              key={summary.groupId}
              type="button"
              onClick={() => onOpenGroup(summary.groupId)}
              className="flex w-full items-center justify-between gap-3 rounded-[20px] border border-slate-100 bg-white px-4 py-3 text-right shadow-sm transition hover:border-emerald-200 hover:bg-emerald-50/30"
            >
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
      className={[
        'inline-flex h-11 flex-1 items-center justify-center gap-2 rounded-[18px] border px-4 text-sm font-extrabold transition sm:flex-none',
        active
          ? 'border-emerald-200 bg-emerald-600 text-white shadow-[0_12px_26px_rgba(16,185,129,0.20)]'
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
    <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
      {Array.from({ length: 4 }).map((_, index) => (
        <div
          key={index}
          className="min-h-[260px] animate-pulse rounded-[30px] border-2 border-slate-100 bg-white p-5 shadow-[0_18px_46px_rgba(15,23,42,0.055)]"
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
  );
}

function EmptyGroupsState({
  filter,
  hasSearch,
  onCreateGroup,
  onResetSearch,
}: {
  filter: GroupFilter;
  hasSearch: boolean;
  onCreateGroup: () => void;
  onResetSearch: () => void;
}) {
  const archived = filter === 'ARCHIVED';

  return (
    <div className="rounded-[30px] border-2 border-dashed border-emerald-200 bg-emerald-50/35 p-8 text-center sm:p-10">
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

      <div className="mt-5 flex flex-col justify-center gap-3 sm:flex-row">
        {hasSearch ? (
          <button
            type="button"
            onClick={onResetSearch}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-[17px] border border-slate-200 bg-white px-5 text-sm font-extrabold text-slate-700 transition hover:bg-slate-50"
          >
            <X className="h-4 w-4" />
            پاک کردن جستجو
          </button>
        ) : null}

        {!archived ? (
          <button
            type="button"
            onClick={onCreateGroup}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-[17px] bg-emerald-600 px-5 text-sm font-extrabold text-white shadow-[0_12px_26px_rgba(16,185,129,0.20)] transition hover:bg-emerald-700"
          >
            <Plus className="h-4 w-4" />
            ساخت گروه جدید
          </button>
        ) : null}
      </div>
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
}: GroupsPageProps) {
  const [filter, setFilter] = useState<GroupFilter>('ACTIVE');
  const [searchTerm, setSearchTerm] = useState('');
  const [inviteModalOpen, setInviteModalOpen] = useState(false);

  const activeGroups = groups.filter((group) => group.status !== 'ARCHIVED');
  const archivedGroups = groups.filter((group) => group.status === 'ARCHIVED');
  const activeCount = activeGroups.length;
  const archivedCount = archivedGroups.length;

  const visibleGroups = useMemo(() => {
    const filteredByStatus = filter === 'ARCHIVED' ? archivedGroups : activeGroups;
    const normalizedSearch = normalizeSearchText(searchTerm);

    if (!normalizedSearch) return filteredByStatus;

    return filteredByStatus.filter((group) =>
      getGroupSearchText(group).includes(normalizedSearch),
    );
  }, [activeGroups, archivedGroups, filter, searchTerm]);

  const hasSearch = Boolean(searchTerm.trim());

  return (
    <>
      <main className="lg:min-h-[calc(100vh-94px)] xl:grid xl:grid-cols-[minmax(0,1fr)_370px]">
        <section className="min-w-0 px-4 py-4 sm:px-6 sm:py-5 xl:px-8">
          <div className="mx-auto max-w-[1020px] space-y-4">
            <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
              <div className="text-right">
                <h1 className="text-[30px] font-extrabold leading-tight tracking-[-0.03em] text-text sm:text-[34px]">
                  گروه‌ها
                </h1>
              </div>

              <div className="grid grid-cols-1 gap-2 sm:flex sm:items-center">
                <button
                  type="button"
                  onClick={() => setInviteModalOpen(true)}
                  className="inline-flex h-12 items-center justify-center gap-2 rounded-[18px] border-2 border-emerald-100 bg-white px-5 text-sm font-extrabold text-emerald-700 shadow-[0_10px_24px_rgba(15,23,42,0.06)] transition hover:-translate-y-0.5 hover:border-emerald-200 hover:bg-emerald-50"
                >
                  <Link2 className="h-5 w-5" />
                  پیوستن با لینک
                </button>

                <button
                  type="button"
                  onClick={onCreateGroup}
                  className="inline-flex h-12 items-center justify-center gap-2 rounded-[18px] bg-gradient-to-l from-[#00915F] to-[#00A86B] px-6 text-sm font-extrabold text-white shadow-[0_14px_30px_rgba(0,168,107,0.22)] transition hover:-translate-y-0.5"
                >
                  <Plus className="h-5 w-5" />
                  ساخت گروه جدید
                </button>
              </div>
            </header>

            <div className="rounded-[28px] border-2 border-slate-200 bg-white p-3 shadow-[0_18px_46px_rgba(15,23,42,0.075)]">
              <div className="grid gap-3 lg:grid-cols-[minmax(260px,1fr)_auto] lg:items-center">
                <div className="relative">
                  <Search className="pointer-events-none absolute right-4 top-1/2 h-4 w-4 -translate-y-1/2 text-emerald-600" />

                  <input
                    dir="rtl"
                    value={searchTerm}
                    onChange={(event) => setSearchTerm(event.target.value)}
                    placeholder="جستجوی گروه؛ مثلاً سفر، خانه، شام..."
                    className="h-12 w-full rounded-[18px] border border-slate-200 bg-slate-50/70 pr-11 pl-11 text-sm font-bold text-text outline-none transition placeholder:font-semibold placeholder:text-slate-400 focus:border-emerald-300 focus:bg-white focus:ring-4 focus:ring-emerald-500/10"
                  />

                  {hasSearch ? (
                    <button
                      type="button"
                      onClick={() => setSearchTerm('')}
                      className="absolute left-3 top-1/2 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded-full border border-slate-100 bg-white text-slate-500 shadow-sm transition hover:border-rose-100 hover:bg-rose-50 hover:text-rose-500"
                      aria-label="پاک کردن جستجو"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  ) : null}
                </div>

                <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap">
                  <FilterButton
                    active={filter === 'ACTIVE'}
                    icon={<CheckCircle2 className="h-4 w-4" />}
                    label="فعال"
                    count={activeCount}
                    onClick={() => setFilter('ACTIVE')}
                  />

                  <FilterButton
                    active={filter === 'ARCHIVED'}
                    icon={<Archive className="h-4 w-4" />}
                    label="آرشیو"
                    count={archivedCount}
                    onClick={() => setFilter('ARCHIVED')}
                  />
                </div>
              </div>

              {hasSearch ? (
                <div className="mt-3 flex flex-wrap items-center justify-between gap-2 px-1 text-xs font-extrabold text-muted">
                  <span>
                    نمایش {toPersianNumber(visibleGroups.length)} گروه از{' '}
                    {toPersianNumber(filter === 'ACTIVE' ? activeCount : archivedCount)}
                  </span>

                  <button
                    type="button"
                    onClick={() => setSearchTerm('')}
                    className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-3 py-1 text-slate-600 transition hover:bg-slate-200"
                  >
                    <RefreshCw className="h-3.5 w-3.5" />
                    حذف جستجو
                  </button>
                </div>
              ) : null}
            </div>

            {error ? (
              <div className="rounded-[26px] border border-rose-100 bg-rose-50 p-5 text-center text-sm font-extrabold text-rose-600">
                {error}
              </div>
            ) : null}

            {loading ? <LoadingState /> : null}

            {!loading && visibleGroups.length === 0 ? (
              <EmptyGroupsState
                filter={filter}
                hasSearch={hasSearch}
                onCreateGroup={onCreateGroup}
                onResetSearch={() => setSearchTerm('')}
              />
            ) : null}

            {!loading && visibleGroups.length > 0 ? (
              <div className="grid gap-5 md:grid-cols-2 2xl:grid-cols-3">
                {visibleGroups.map((group) => (
                  <GroupCard
                    key={group.id}
                    group={group}
                    onOpen={() => onOpenGroup(String(group.id))}
                    onDelete={onDeleteGroup}
                  />
                ))}
              </div>
            ) : null}
          </div>
        </section>

        <aside className="px-4 pb-8 sm:px-6 xl:w-[370px] xl:px-8 xl:py-5">
          <div className="sticky top-5 space-y-5">
            <GroupDebtsSummaryCard
              summaries={groupBalances}
              loading={balancesLoading}
              onOpenGroup={onOpenGroup}
            />
          </div>
        </aside>
      </main>

      <JoinInviteModal
        open={inviteModalOpen}
        onClose={() => setInviteModalOpen(false)}
        onOpenInvite={onOpenInvite}
      />
    </>
  );
}