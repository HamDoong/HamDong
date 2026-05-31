import { useEffect, useState } from 'react';
import { Plus } from 'lucide-react';
import { AccountSummary } from './components/AccountSummary';
import { CreateGroupForm } from './components/CreateGroupForm';
import { GroupCard } from './components/GroupCard';
import { MobileDrawer } from './components/MobileDrawer';
import { RecentActivities } from './components/RecentActivities';
import { RecentMembers } from './components/RecentMembers';
import { Sidebar } from './components/Sidebar';
import { TopBar } from './components/TopBar';
import { Button } from './components/ui/Button';
import { groups } from './data/mockData';

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

function DashboardHeader() {
  return (
    <div className="mb-8 flex flex-col items-start justify-between gap-5 xl:flex-row xl:items-center">
      <div className="text-right">
        <h1 className="text-[32px] font-extrabold leading-tight tracking-[-0.03em] text-text">
          گروه‌ها
        </h1>
        <p className="mt-2 text-base text-muted">
          مدیریت گروه‌های شما و مشاهده جزئیات آن‌ها
        </p>
      </div>

      <Button className="h-12 shrink-0 px-6 text-base font-semibold">
        <Plus className="h-5 w-5" />
        تشکیل گروه جدید
      </Button>
    </div>
  );
}

function MainContent() {
  return (
    <section className="min-w-0 px-4 py-6 sm:px-6 sm:py-8 xl:px-8">
      <div className="mx-auto max-w-[920px]">
        <DashboardHeader />

        <div className="grid gap-6 md:grid-cols-2 2xl:grid-cols-3">
          {groups.map((group) => (
            <GroupCard key={group.id} group={group} />
          ))}
        </div>

        <CarouselDots />
        <CreateGroupForm />
      </div>
    </section>
  );
}

function InfoPanel() {
  return (
    <aside className="px-4 pb-8 sm:px-6 xl:w-[354px] xl:px-8 xl:py-8">
      <div className="space-y-6">
        <AccountSummary />
        <RecentMembers />
        <RecentActivities />
      </div>
    </aside>
  );
}

export default function App() {
  const [isMobileDrawerOpen, setIsMobileDrawerOpen] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(min-width: 1024px)');

    const handleChange = (event: MediaQueryListEvent | MediaQueryList) => {
      if (event.matches) {
        setIsMobileDrawerOpen(false);
      }
    };

    handleChange(mediaQuery);

    if (typeof mediaQuery.addEventListener === 'function') {
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }

    mediaQuery.addListener(handleChange);
    return () => mediaQuery.removeListener(handleChange);
  }, []);

  useEffect(() => {
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = isMobileDrawerOpen ? 'hidden' : originalOverflow;

    return () => {
      document.body.style.overflow = originalOverflow;
    };
  }, [isMobileDrawerOpen]);

  return (
    <div dir="rtl" className="min-h-screen bg-background text-text">
      <MobileDrawer
        open={isMobileDrawerOpen}
        onClose={() => setIsMobileDrawerOpen(false)}
      />

      <div className="mx-auto min-h-screen max-w-[1536px] lg:grid lg:grid-cols-[236px_minmax(0,1fr)]">
        <Sidebar className="hidden lg:flex lg:h-screen lg:w-[236px] lg:shrink-0 lg:border-l lg:border-border/90" />

        <div className="min-w-0">
          <TopBar onMenuClick={() => setIsMobileDrawerOpen(true)} />

          <main className="lg:min-h-[calc(100vh-94px)] xl:grid xl:grid-cols-[minmax(0,1fr)_354px]">
            <MainContent />
            <InfoPanel />
          </main>
        </div>
      </div>
    </div>
  );
}