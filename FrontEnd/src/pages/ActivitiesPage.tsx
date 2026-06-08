import { useMemo, useState } from 'react';
import {
  ArrowDown,
  ArrowUp,
  CalendarDays,
  ChevronDown,
  CircleDollarSign,
  Filter,
  Grid2X2,
  History,
  Layers3,
  PieChart,
  RefreshCw,
  Search,
  SlidersHorizontal,
  Star,
  User,
  Users,
  WalletCards,
} from 'lucide-react';

type ActivityKind = 'all' | 'received' | 'paid' | 'settlement';
type ActivityStatus = 'received' | 'paid' | 'settled';
type ActivityDirection = 'in' | 'out' | 'wallet';

interface ActivityItem {
  id: number;
  title: string;
  group: string;
  groupIcon: string;
  person: string;
  avatarInitial: string;
  avatarClassName: string;
  time: string;
  dateGroup: string;
  amount: number;
  status: ActivityStatus;
  direction: ActivityDirection;
  kind: Exclude<ActivityKind, 'all'>;
}

const activities: ActivityItem[] = [
  {
    id: 1,
    title: 'سارا محمدی سهم خود را پرداخت کرد',
    group: 'سفر شمال تابستان ۱۴۰۳',
    groupIcon: '🏝️',
    person: 'سارا محمدی',
    avatarInitial: 'س',
    avatarClassName: 'from-fuchsia-300 to-purple-600',
    time: '۱۴:۳۵',
    dateGroup: 'امروز - سه‌شنبه ۱ خرداد ۱۴۰۳',
    amount: 120000,
    status: 'received',
    direction: 'in',
    kind: 'received',
  },
  {
    id: 2,
    title: 'شما هزینه شام را پرداخت کردید',
    group: 'کافه دوستان',
    groupIcon: '☕',
    person: 'شما',
    avatarInitial: 'ع',
    avatarClassName: 'from-teal-300 to-emerald-700',
    time: '۱۲:۴۰',
    dateGroup: 'امروز - سه‌شنبه ۱ خرداد ۱۴۰۳',
    amount: -250000,
    status: 'paid',
    direction: 'out',
    kind: 'paid',
  },
  {
    id: 3,
    title: 'رضا کریمی سهم خود را پرداخت کرد',
    group: 'خانه ما',
    groupIcon: '🏢',
    person: 'رضا کریمی',
    avatarInitial: 'ر',
    avatarClassName: 'from-amber-300 to-orange-600',
    time: '۱۱:۱۰',
    dateGroup: 'امروز - سه‌شنبه ۱ خرداد ۱۴۰۳',
    amount: 75600,
    status: 'received',
    direction: 'in',
    kind: 'received',
  },
  {
    id: 4,
    title: 'مینا حسینی سهم خود را پرداخت کرد',
    group: 'سفر شمال تابستان ۱۴۰۳',
    groupIcon: '🏝️',
    person: 'مینا حسینی',
    avatarInitial: 'م',
    avatarClassName: 'from-sky-300 to-cyan-600',
    time: '۲۰:۱۵',
    dateGroup: 'دیروز - دوشنبه ۳۱ اردیبهشت ۱۴۰۳',
    amount: 34250,
    status: 'received',
    direction: 'in',
    kind: 'received',
  },
  {
    id: 5,
    title: 'شما هزینه تاکسی را پرداخت کردید',
    group: 'سفر شمال تابستان ۱۴۰۳',
    groupIcon: '🏝️',
    person: 'شما',
    avatarInitial: 'ع',
    avatarClassName: 'from-teal-300 to-emerald-700',
    time: '۱۸:۴۰',
    dateGroup: 'دیروز - دوشنبه ۳۱ اردیبهشت ۱۴۰۳',
    amount: -150000,
    status: 'paid',
    direction: 'out',
    kind: 'paid',
  },
  {
    id: 6,
    title: 'حامد نوروزی سهم خود را پرداخت کرد',
    group: 'کافه دوستان',
    groupIcon: '☕',
    person: 'حامد نوروزی',
    avatarInitial: 'ح',
    avatarClassName: 'from-slate-400 to-slate-700',
    time: '۱۶:۲۸',
    dateGroup: 'یکشنبه ۳۰ اردیبهشت ۱۴۰۳',
    amount: 60000,
    status: 'received',
    direction: 'in',
    kind: 'received',
  },
  {
    id: 7,
    title: 'تسویه خودکار با کیف پول',
    group: 'خانه ما',
    groupIcon: '🏢',
    person: 'سیستم',
    avatarInitial: 'ک',
    avatarClassName: 'from-emerald-300 to-teal-700',
    time: '۱۰:۰۰',
    dateGroup: 'یکشنبه ۳۰ اردیبهشت ۱۴۰۳',
    amount: 80000,
    status: 'settled',
    direction: 'wallet',
    kind: 'settlement',
  },
];

function formatMoney(amount: number) {
  const prefix = amount > 0 ? '+' : amount < 0 ? '-' : '';
  const absValue = Math.abs(amount).toLocaleString('en-US');

  return `${prefix}${absValue}`;
}

function statusLabel(status: ActivityStatus) {
  if (status === 'received') return 'دریافت شد';
  if (status === 'paid') return 'پرداخت شد';
  return 'تسویه شد';
}

function statusClasses(status: ActivityStatus) {
  if (status === 'received') return 'bg-emerald-50 text-emerald-700';
  if (status === 'paid') return 'bg-rose-50 text-rose-600';
  return 'bg-sky-50 text-sky-600';
}

function directionIcon(direction: ActivityDirection) {
  if (direction === 'in') {
    return <ArrowDown className="h-5 w-5" />;
  }

  if (direction === 'out') {
    return <ArrowUp className="h-5 w-5" />;
  }

  return <WalletCards className="h-5 w-5" />;
}

function directionClasses(direction: ActivityDirection) {
  if (direction === 'in') return 'bg-emerald-50 text-emerald-600';
  if (direction === 'out') return 'bg-rose-50 text-rose-500';
  return 'bg-emerald-50 text-emerald-600';
}

function SelectLike({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <button
      type="button"
      className="inline-flex h-12 min-w-[148px] items-center justify-between gap-3 rounded-2xl border border-border bg-white px-4 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-emerald-200 hover:text-emerald-700"
    >
      <span className="flex items-center gap-2">
        {icon}
        {label}
      </span>
      <ChevronDown className="h-4 w-4 text-slate-500" />
    </button>
  );
}

function FilterPill({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        'h-10 rounded-2xl px-4 text-sm font-bold transition',
        active
          ? 'bg-emerald-600 text-white shadow-[0_12px_28px_rgba(0,168,107,0.18)]'
          : 'border border-border bg-white text-slate-600 hover:border-emerald-200 hover:text-emerald-700',
      ].join(' ')}
    >
      {label}
    </button>
  );
}

function ActivityRow({ item }: { item: ActivityItem }) {
  return (
    <div className="grid gap-4 border-b border-border px-5 py-4 last:border-b-0 md:grid-cols-[150px_minmax(0,1fr)_82px_52px] md:items-center">
      <div className="flex items-center justify-between gap-3 md:justify-start">
        <div
          className={[
            'text-[24px] font-black tracking-[-0.03em]',
            item.amount >= 0 ? 'text-emerald-600' : 'text-rose-500',
          ].join(' ')}
          dir="ltr"
        >
          {formatMoney(item.amount)}
        </div>
        <span className="text-sm font-bold text-emerald-700">تومان</span>
      </div>

      <div className="flex min-w-0 items-center justify-end gap-4 text-right">
        <div className="min-w-0">
          <h3 className="truncate text-base font-bold text-text">{item.title}</h3>
          <p className="mt-1 truncate text-sm text-muted">
            {item.group} <span className="mr-1">{item.groupIcon}</span>
          </p>
        </div>

        <div
          className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-gradient-to-br text-sm font-bold text-white shadow-sm ${item.avatarClassName}`}
          title={item.person}
        >
          {item.avatarInitial}
        </div>
      </div>

      <div className="flex items-center gap-3 md:justify-center">
        <span className={`rounded-xl px-3 py-2 text-xs font-bold ${statusClasses(item.status)}`}>
          {statusLabel(item.status)}
        </span>
        <span className="text-sm text-muted md:hidden">{item.time}</span>
      </div>

      <div className="flex items-center justify-between gap-3 md:justify-end">
        <span className="hidden text-sm text-muted md:inline">{item.time}</span>
        <div
          className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-full ${directionClasses(
            item.direction,
          )}`}
        >
          {directionIcon(item.direction)}
        </div>
      </div>
    </div>
  );
}

function ActivityDateGroup({ date, items }: { date: string; items: ActivityItem[] }) {
  return (
    <section>
      <h2 className="mb-4 text-right text-lg font-extrabold text-text">{date}</h2>
      <div className="overflow-hidden rounded-3xl border border-border bg-white shadow-soft">
        {items.map((item) => (
          <ActivityRow key={item.id} item={item} />
        ))}
      </div>
    </section>
  );
}

function FilterSidebar({
  currentKind,
  onChangeKind,
}: {
  currentKind: ActivityKind;
  onChangeKind: (kind: ActivityKind) => void;
}) {
  return (
    <aside className="space-y-5">
      <div className="rounded-3xl border border-border bg-white p-6 shadow-soft">
        <div className="mb-6 flex items-center justify-between">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600">
            <SlidersHorizontal className="h-5 w-5" />
          </div>
          <h2 className="text-xl font-extrabold text-text">فیلترها</h2>
        </div>

        <div className="space-y-5 text-right">
          <div>
            <label className="mb-2 block text-sm font-semibold text-muted">بازه زمانی</label>
            <button className="flex h-12 w-full items-center justify-between rounded-2xl border border-border bg-white px-4 text-sm font-semibold text-text">
              <ChevronDown className="h-4 w-4 text-slate-500" />
              ماه جاری
            </button>
          </div>

          <div>
            <label className="mb-2 block text-sm font-semibold text-muted">نوع فعالیت</label>
            <div className="grid grid-cols-2 gap-2">
              <FilterPill active={currentKind === 'all'} label="همه" onClick={() => onChangeKind('all')} />
              <FilterPill active={currentKind === 'received'} label="دریافت" onClick={() => onChangeKind('received')} />
              <FilterPill active={currentKind === 'paid'} label="پرداخت" onClick={() => onChangeKind('paid')} />
              <FilterPill active={currentKind === 'settlement'} label="تسویه" onClick={() => onChangeKind('settlement')} />
            </div>
          </div>

          <button className="h-12 w-full rounded-2xl bg-gradient-to-l from-[#00915F] to-[#00A86B] text-sm font-extrabold text-white shadow-[0_12px_28px_rgba(0,168,107,0.20)] transition hover:-translate-y-0.5">
            اعمال فیلتر
          </button>
        </div>
      </div>

      <div className="rounded-3xl border border-border bg-white p-6 shadow-soft">
        <div className="mb-6 flex items-center justify-between">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600">
            <PieChart className="h-5 w-5" />
          </div>
          <h2 className="text-xl font-extrabold text-text">خلاصه فعالیت‌ها</h2>
        </div>

        <div className="space-y-4 text-sm">
          <div className="flex items-center justify-between">
            <span className="font-extrabold text-emerald-600" dir="ltr">+289,850</span>
            <span className="text-muted">دریافت‌ها</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="font-extrabold text-rose-500" dir="ltr">-400,000</span>
            <span className="text-muted">پرداخت‌ها</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="font-extrabold text-sky-500" dir="ltr">+80,000</span>
            <span className="text-muted">تسویه‌ها</span>
          </div>

          <div className="my-4 h-px bg-border" />

          <div className="flex items-center justify-between">
            <span className="font-extrabold text-rose-500" dir="ltr">-30,150</span>
            <span className="text-muted">خالص جریان</span>
          </div>
        </div>
      </div>

      <div className="rounded-3xl border border-border bg-white p-6 text-center shadow-soft">
        <div className="mb-4 flex items-center justify-between text-right">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600">
            <Star className="h-5 w-5" />
          </div>
          <h2 className="text-xl font-extrabold text-text">پر‌فعال‌ترین گروه</h2>
        </div>

        <div className="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-b from-sky-100 to-amber-100 text-4xl shadow-inner">
          🏝️
        </div>
        <h3 className="text-base font-extrabold text-text">سفر شمال تابستان ۱۴۰۳</h3>
        <p className="mt-1 text-sm text-muted">۸ فعالیت</p>
        <button className="mt-5 h-11 w-full rounded-2xl bg-slate-50 text-sm font-bold text-slate-700 transition hover:bg-emerald-50 hover:text-emerald-700">
          مشاهده جزئیات
        </button>
      </div>
    </aside>
  );
}

export function ActivitiesPage() {
  const [kind, setKind] = useState<ActivityKind>('all');
  const [visibleCount, setVisibleCount] = useState(7);

  const filteredActivities = useMemo(() => {
    if (kind === 'all') return activities;
    return activities.filter((item) => item.kind === kind);
  }, [kind]);

  const visibleActivities = filteredActivities.slice(0, visibleCount);

  const groupedActivities = useMemo(() => {
    return visibleActivities.reduce<Record<string, ActivityItem[]>>((acc, item) => {
      acc[item.dateGroup] = acc[item.dateGroup] || [];
      acc[item.dateGroup].push(item);
      return acc;
    }, {});
  }, [visibleActivities]);

  return (
    <main className="min-h-[calc(100vh-94px)] px-4 py-6 sm:px-6 xl:px-8">
      <div className="mx-auto max-w-[1280px]">
        <div className="mb-8 grid gap-5 lg:grid-cols-[320px_minmax(0,1fr)] lg:items-start">
          <div className="order-2 lg:order-1">
            <FilterSidebar currentKind={kind} onChangeKind={setKind} />
          </div>

          <section className="order-1 min-w-0 space-y-6 lg:order-2">
            <div className="flex flex-col items-start justify-between gap-5 xl:flex-row xl:items-end">
              <div className="text-right">
                <h1 className="text-[32px] font-extrabold leading-tight tracking-[-0.03em] text-text">
                  فعالیت‌ها
                </h1>
                <p className="mt-2 text-base text-muted">
                  تاریخچه تمام فعالیت‌ها و تراکنش‌های شما
                </p>
              </div>
            </div>

            <div className="rounded-3xl border border-emerald-100 bg-emerald-50/50 p-4 text-right shadow-soft">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-white text-emerald-600 shadow-sm">
                  <History className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-sm font-extrabold text-emerald-700">امروز - سه‌شنبه ۱ خرداد ۱۴۰۳</p>
                  <p className="mt-1 text-xs text-muted">نمایش {filteredActivities.length.toLocaleString('fa-IR')} فعالیت نمونه برای طراحی UI</p>
                </div>
              </div>
            </div>

            <div className="space-y-7">
              {Object.entries(groupedActivities).map(([date, items]) => (
                <ActivityDateGroup key={date} date={date} items={items} />
              ))}
            </div>

            {visibleCount < filteredActivities.length ? (
              <div className="flex justify-center pt-2">
                <button
                  type="button"
                  onClick={() => setVisibleCount((prev) => prev + 4)}
                  className="inline-flex h-12 items-center gap-2 rounded-2xl border border-border bg-white px-7 text-sm font-extrabold text-slate-700 shadow-sm transition hover:border-emerald-200 hover:text-emerald-700"
                >
                  بارگذاری بیشتر
                  <ChevronDown className="h-4 w-4" />
                </button>
              </div>
            ) : null}
          </section>
        </div>
      </div>
    </main>
  );
}
