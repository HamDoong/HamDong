import { Plus } from 'lucide-react';
import { AccountSummary } from '../components/AccountSummary';
import { GroupCard } from '../components/GroupCard';
import { RecentActivities } from '../components/RecentActivities';
import { RecentMembers } from '../components/RecentMembers';
import { groups as mockGroups } from '../data/mockData';

type DashboardGroup = (typeof mockGroups)[number];

interface GroupsPageProps {
  groups: DashboardGroup[];
  onCreateGroup: () => void;
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

export function GroupsPage({ groups, onCreateGroup }: GroupsPageProps) {
  return (
    <main className="lg:min-h-[calc(100vh-94px)] xl:grid xl:grid-cols-[minmax(0,1fr)_354px]">
      <section className="min-w-0 px-4 py-6 sm:px-6 sm:py-8 xl:px-8">
        <div className="mx-auto max-w-[920px]">
          <div className="mb-8 flex flex-col items-start justify-between gap-5 xl:flex-row xl:items-center">
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

          <div className="grid gap-6 md:grid-cols-2 2xl:grid-cols-3">
            {groups.map((group) => (
              <GroupCard key={group.id} group={group} />
            ))}
          </div>

          <CarouselDots />
        </div>
      </section>

      <aside className="px-4 pb-8 sm:px-6 xl:w-[354px] xl:px-8 xl:py-8">
        <div className="space-y-6">
          <AccountSummary />
          <RecentMembers />
          <RecentActivities />
        </div>
      </aside>
    </main>
  );
}