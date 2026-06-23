import { Archive, CheckCircle2, HandCoins, Link2, Plus, Users } from 'lucide-react';
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

function formatMoney(minor = 0) {
  return `${Math.abs(Math.round(minor)).toLocaleString('fa-IR')} تومان`;
}

function JoinByInviteCard({ onOpenInvite }: { onOpenInvite: (tokenOrLink: string) => void }) {
  const [inviteValue, setInviteValue] = useState('');

  const token = extractInviteToken(inviteValue);

  const handleSubmit = () => {
    if (!token) return;

    onOpenInvite(token);
    setInviteValue('');
  };

  return (
    <div className="rounded-3xl border border-emerald-100 bg-emerald-50/45 p-6 shadow-soft">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div className="text-right">
          <h2 className="text-xl font-extrabold text-text">پیوستن با لینک دعوت</h2>
          <p className="mt-1 text-sm leading-7 text-muted">
            لینک دعوتی که دریافت کردی را وارد کن تا جزئیات گروه را ببینی.
          </p>
        </div>
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-white text-emerald-600 shadow-sm">
          <Link2 className="h-5 w-5" />
        </div>
      </div>

      <input
        dir="ltr"
        value={inviteValue}
        onChange={(event) => setInviteValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter') handleSubmit();
        }}
        placeholder="لینک دعوت را اینجا وارد کن"
        className="h-12 w-full rounded-2xl border border-border bg-white px-4 text-left text-sm text-slate-700 outline-none transition placeholder:text-slate-400 focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
      />

      <button
        type="button"
        onClick={handleSubmit}
        disabled={!token}
        className="mt-3 inline-flex h-11 w-full items-center justify-center rounded-2xl bg-gradient-to-l from-[#00915F] to-[#00A86B] px-5 text-sm font-bold text-white shadow-[0_12px_28px_rgba(0,168,107,0.18)] transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-50"
      >
        بررسی دعوت
      </button>
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
    <div className="rounded-3xl border border-border bg-white p-6 shadow-soft">
      <div className="mb-5 flex items-center justify-between gap-3">
        <div className="text-right">
          <h2 className="text-xl font-extrabold text-text">خلاصه حساب گروه‌ها</h2>
          <p className="mt-1 text-sm leading-7 text-muted">
            وضعیت بدهکاری و طلبکاری شما بر اساس هزینه‌های ثبت‌شده.
          </p>
        </div>
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600">
          <HandCoins className="h-5 w-5" />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-2xl bg-rose-50 px-4 py-3 text-right">
          <div className="text-xs font-semibold text-rose-500">کل بدهی شما</div>
          <div className="mt-1 text-base font-extrabold text-rose-600">{formatMoney(totalDebtMinor)}</div>
        </div>
        <div className="rounded-2xl bg-emerald-50 px-4 py-3 text-right">
          <div className="text-xs font-semibold text-emerald-600">کل طلب شما</div>
          <div className="mt-1 text-base font-extrabold text-emerald-700">{formatMoney(totalCreditMinor)}</div>
        </div>
      </div>

      {loading ? (
        <div className="mt-4 rounded-2xl border border-border bg-slate-50 p-4 text-center text-sm text-muted">
          در حال محاسبه حساب گروه‌ها...
        </div>
      ) : null}

      {!loading && activeSummaries.length === 0 ? (
        <div className="mt-4 rounded-2xl border border-dashed border-border p-5 text-center text-sm leading-7 text-muted">
          هنوز هزینه‌ای برای محاسبه حساب گروه‌ها ثبت نشده است.
        </div>
      ) : null}

      <div className="mt-4 space-y-3">
        {activeSummaries.map((summary) => {
          const isDebt = summary.netMinor < 0;
          const isCredit = summary.netMinor > 0;

          return (
            <button
              key={summary.groupId}
              type="button"
              onClick={() => onOpenGroup(summary.groupId)}
              className="flex w-full items-center justify-between gap-3 rounded-2xl border border-border bg-white px-4 py-3 text-right transition hover:border-emerald-200 hover:bg-emerald-50/30"
            >
              <div className="min-w-0">
                <div className="truncate text-sm font-bold text-text">{summary.groupName}</div>
                <div className="mt-1 text-xs text-muted">
                  {isDebt ? 'برای پرداخت بدهی وارد گروه شو' : isCredit ? 'در این گروه طلبکار هستی' : 'این گروه تسویه است'}
                </div>
              </div>

              <div className="shrink-0 text-left">
                <div className={['text-sm font-extrabold', isDebt ? 'text-rose-600' : isCredit ? 'text-emerald-600' : 'text-slate-500'].join(' ')}>
                  {formatMoney(summary.netMinor)}
                </div>
                <div className="mt-1 text-xs text-muted">
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
        'inline-flex h-11 items-center gap-2 rounded-2xl border px-4 text-sm font-bold transition',
        active
          ? 'border-emerald-200 bg-emerald-50 text-emerald-700 shadow-[0_10px_24px_rgba(0,168,107,0.08)]'
          : 'border-border bg-white text-slate-600 hover:border-emerald-200 hover:text-emerald-700',
      ].join(' ')}
    >
      {icon}
      {label}
      <span className="rounded-full bg-white px-2 py-0.5 text-xs text-slate-500">
        {count.toLocaleString('fa-IR')}
      </span>
    </button>
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

  const activeCount = groups.filter((group) => group.status !== 'ARCHIVED').length;
  const archivedCount = groups.filter((group) => group.status === 'ARCHIVED').length;

  const visibleGroups = useMemo(() => {
    if (filter === 'ARCHIVED') {
      return groups.filter((group) => group.status === 'ARCHIVED');
    }

    return groups.filter((group) => group.status !== 'ARCHIVED');
  }, [groups, filter]);

  return (
    <main className="lg:min-h-[calc(100vh-94px)] xl:grid xl:grid-cols-[minmax(0,1fr)_354px]">
      <section className="min-w-0 px-4 py-6 sm:px-6 sm:py-8 xl:px-8">
        <div className="mx-auto max-w-[920px]">
          <div className="mb-6 flex flex-col items-start justify-between gap-5 xl:flex-row xl:items-center">
            <div className="text-right">
              <h1 className="text-[32px] font-extrabold leading-tight tracking-[-0.03em] text-text">
                گروه‌ها
              </h1>
              <p className="mt-2 text-base text-muted">
                مدیریت گروه‌ها، دعوت اعضا و مشاهده وضعیت حساب هر گروه
              </p>
            </div>

            <button
              type="button"
              onClick={onCreateGroup}
              className="inline-flex h-12 shrink-0 items-center gap-2 rounded-[16px] bg-gradient-to-l from-[#00915F] to-[#00A86B] px-6 text-base font-semibold text-white shadow-[0_12px_28px_rgba(0,168,107,0.22)] transition hover:-translate-y-0.5"
            >
              <Plus className="h-5 w-5" />
              تشکیل گروه جدید
            </button>
          </div>

          <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-3xl border border-border bg-white p-3 shadow-soft">
            <div className="flex flex-wrap gap-2">
              <FilterButton active={filter === 'ACTIVE'} icon={<CheckCircle2 className="h-4 w-4" />} label="گروه‌های فعال" count={activeCount} onClick={() => setFilter('ACTIVE')} />
              <FilterButton active={filter === 'ARCHIVED'} icon={<Archive className="h-4 w-4" />} label="گروه‌های آرشیو شده" count={archivedCount} onClick={() => setFilter('ARCHIVED')} />
            </div>
            <span className="px-2 text-xs font-semibold text-muted">
              نمایش فعلی: {filter === 'ACTIVE' ? 'فعال' : 'آرشیو شده'}
            </span>
          </div>

          {loading ? (
            <div className="rounded-3xl border border-border bg-white p-8 text-center text-muted shadow-soft">
              در حال دریافت گروه‌ها...
            </div>
          ) : null}

          {error ? (
            <div className="mb-6 rounded-3xl border border-rose-100 bg-rose-50 p-6 text-center text-rose-600">
              {error}
            </div>
          ) : null}

          {!loading && visibleGroups.length === 0 ? (
            <div className="rounded-3xl border border-dashed border-emerald-200 bg-emerald-50/40 p-10 text-center">
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-3xl bg-white text-emerald-600 shadow-sm">
                {filter === 'ARCHIVED' ? <Archive className="h-7 w-7" /> : <Users className="h-7 w-7" />}
              </div>
              <h2 className="text-xl font-bold text-text">
                {filter === 'ARCHIVED' ? 'گروه آرشیو شده‌ای نداری' : 'هنوز گروه فعالی نداری'}
              </h2>
              <p className="mt-2 text-sm leading-7 text-muted">
                {filter === 'ARCHIVED'
                  ? 'وقتی گروهی را آرشیو کنی، از لیست فعال‌ها خارج می‌شود و اینجا دیده می‌شود.'
                  : 'اولین گروهت را بساز تا هزینه‌ها، اعضا و دعوت‌ها را مدیریت کنی.'}
              </p>
              {filter === 'ACTIVE' ? (
                <button type="button" onClick={onCreateGroup} className="mt-5 inline-flex h-11 items-center justify-center rounded-2xl bg-emerald-600 px-5 text-sm font-semibold text-white transition hover:bg-emerald-700">
                  ساخت اولین گروه
                </button>
              ) : null}
            </div>
          ) : null}

          {!loading && visibleGroups.length > 0 ? (
            <div className="grid gap-6 md:grid-cols-2 2xl:grid-cols-3">
              {visibleGroups.map((group) => (
                <GroupCard key={group.id} group={group} onOpen={() => onOpenGroup(String(group.id))} onDelete={onDeleteGroup} />
              ))}
            </div>
          ) : null}
        </div>
      </section>

      <aside className="px-4 pb-8 sm:px-6 xl:w-[354px] xl:px-8 xl:py-8">
        <div className="space-y-6">
          <JoinByInviteCard onOpenInvite={onOpenInvite} />
          <GroupDebtsSummaryCard summaries={groupBalances} loading={balancesLoading} onOpenGroup={onOpenGroup} />
        </div>
      </aside>
    </main>
  );
}
