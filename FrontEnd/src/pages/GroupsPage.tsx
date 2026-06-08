import { Archive, CheckCircle2, Link2, Plus, Users } from 'lucide-react';
import { useMemo, useState, type ReactNode } from 'react';
import { AccountSummary } from '../components/AccountSummary';
import { GroupCard } from '../components/GroupCard';
import { RecentActivities } from '../components/RecentActivities';
import { RecentMembers } from '../components/RecentMembers';
import { extractInviteToken } from '../lib/groupApi';
import type { Group, GroupStatus } from '../types';

type GroupFilter = 'ACTIVE' | 'ARCHIVED';

interface GroupsPageProps {
  groups: Group[];
  loading?: boolean;
  error?: string | null;
  onCreateGroup: () => void;
  onOpenGroup: (groupId: string) => void;
  onOpenInvite: (tokenOrLink: string) => void;
  onDeleteGroup: (group: Group) => void;
}

function CarouselDots() {
  return (
    <div className="my-8 flex items-center justify-center gap-2.5">
      <span className="h-1.5 w-10 rounded-full bg-emerald-500" />
      <span className="h-1.5 w-5 rounded-full bg-slate-200" />
      <span className="h-1.5 w-5 rounded-full bg-slate-200" />
      <span className="h-1.5 w-5 rounded-full bg-slate-200" />
    </div>
  );
}

function JoinByInviteCard({ onOpenInvite }: { onOpenInvite: (tokenOrLink: string) => void }) {
  const [inviteValue, setInviteValue] = useState('');

  const handleSubmit = () => {
    const token = extractInviteToken(inviteValue);

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
            لینک دعوتی که دریافت کردی را اینجا وارد کن تا جزئیات گروه را ببینی.
          </p>
        </div>
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-white text-emerald-600 shadow-sm">
          <Link2 className="h-5 w-5" />
        </div>
      </div>

      <div className="relative">
        <input
          dir="ltr"
          value={inviteValue}
          onChange={(event) => setInviteValue(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') handleSubmit();
          }}
          placeholder="https://.../invites/token"
          className="h-12 w-full rounded-2xl border border-border bg-white px-4 text-left text-sm text-slate-700 outline-none transition placeholder:text-slate-400 focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
        />
      </div>

      <button
        type="button"
        onClick={handleSubmit}
        disabled={!extractInviteToken(inviteValue)}
        className="mt-3 inline-flex h-11 w-full items-center justify-center rounded-2xl bg-gradient-to-l from-[#00915F] to-[#00A86B] px-5 text-sm font-bold text-white shadow-[0_12px_28px_rgba(0,168,107,0.18)] transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-50"
      >
        بررسی دعوت
      </button>
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
                مدیریت گروه‌های شما و مشاهده جزئیات آن‌ها
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
              <FilterButton
                active={filter === 'ACTIVE'}
                icon={<CheckCircle2 className="h-4 w-4" />}
                label="گروه‌های فعال"
                count={activeCount}
                onClick={() => setFilter('ACTIVE')}
              />
              <FilterButton
                active={filter === 'ARCHIVED'}
                icon={<Archive className="h-4 w-4" />}
                label="گروه‌های آرشیو شده"
                count={archivedCount}
                onClick={() => setFilter('ARCHIVED')}
              />
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
                <button
                  type="button"
                  onClick={onCreateGroup}
                  className="mt-5 inline-flex h-11 items-center justify-center rounded-2xl bg-emerald-600 px-5 text-sm font-semibold text-white transition hover:bg-emerald-700"
                >
                  ساخت اولین گروه
                </button>
              ) : null}
            </div>
          ) : null}

          {!loading && visibleGroups.length > 0 ? (
            <div className="grid gap-6 md:grid-cols-2 2xl:grid-cols-3">
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

          {visibleGroups.length > 3 ? <CarouselDots /> : null}
        </div>
      </section>

      <aside className="px-4 pb-8 sm:px-6 xl:w-[354px] xl:px-8 xl:py-8">
        <div className="space-y-6">
          <JoinByInviteCard onOpenInvite={onOpenInvite} />
          <AccountSummary />
          <RecentMembers />
          <RecentActivities />
        </div>
      </aside>
    </main>
  );
}
