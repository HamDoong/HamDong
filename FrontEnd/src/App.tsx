import { useEffect, useState } from 'react';
import { MobileDrawer } from './components/MobileDrawer';
import { Sidebar } from './components/Sidebar';
import { TopBar } from './components/TopBar';
import { groups as mockGroups } from './data/mockData';
import {
  CreateGroupWizard,
  type CreatedGroupPayload,
} from './pages/CreateGroupWizard';
import { GroupsPage } from './pages/GroupsPage';
import { LandingPage } from './pages/LandingPage';

type AppPage = 'landing' | 'groups' | 'create-group';
type DashboardGroup = (typeof mockGroups)[number];

function mapCreatedGroupToDashboardGroup(
  payload: CreatedGroupPayload,
): DashboardGroup {
  const baseGroup = mockGroups[0]!;
  const normalizedAmount = payload.amount.replace(/[^\d-]/g, '');
  const amountValue = Number(normalizedAmount || '0');

  const illustration: DashboardGroup['illustration'] =
    payload.groupType === 'travel'
      ? 'trip'
      : payload.groupType === 'food'
        ? 'cafe'
        : payload.groupType === 'home'
          ? 'home'
          : baseGroup.illustration;

  return {
    ...baseGroup,
    id: Date.now(),
    name: payload.name || 'گروه جدید',
    membersLabel: `${payload.memberCount.toLocaleString('fa-IR')} عضو • فعال`,
    statusLabel: amountValue > 0 ? 'شما طلبکار هستید' : 'تراز این گروه صفر است',
    amount: `${amountValue > 0 ? '+' : ''}${amountValue.toLocaleString('fa-IR')} تومان`,
    tone: amountValue < 0 ? 'negative' : 'positive',
    illustration,
  };
}

export default function App() {
  const [page, setPage] = useState<AppPage>('landing');
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);
  const [groupItems, setGroupItems] = useState<DashboardGroup[]>(mockGroups);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(min-width: 1024px)');

    const handleChange = (event: MediaQueryListEvent | MediaQueryList) => {
      if (event.matches) {
        setMobileDrawerOpen(false);
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
    document.body.style.overflow = mobileDrawerOpen ? 'hidden' : originalOverflow;

    return () => {
      document.body.style.overflow = originalOverflow;
    };
  }, [mobileDrawerOpen]);

  const handleCreateGroupComplete = (payload: CreatedGroupPayload) => {
    setGroupItems((prev) => [mapCreatedGroupToDashboardGroup(payload), ...prev]);
    setPage('groups');
  };

  if (page === 'landing') {
    return (
      <div dir="rtl" className="min-h-screen bg-background text-text">
        <LandingPage onStart={() => setPage('groups')} />
      </div>
    );
  }

  return (
    <div dir="rtl" className="min-h-screen bg-background text-text">
      <MobileDrawer
        open={mobileDrawerOpen}
        onClose={() => setMobileDrawerOpen(false)}
      />

      <div className="mx-auto min-h-screen max-w-[1536px] lg:grid lg:grid-cols-[236px_minmax(0,1fr)]">
        <Sidebar className="hidden lg:flex lg:h-screen lg:w-[236px] lg:shrink-0 lg:border-l lg:border-border/90" />

        <div className="min-w-0">
          <TopBar onMenuClick={() => setMobileDrawerOpen(true)} />

          {page === 'groups' ? (
            <GroupsPage
              groups={groupItems}
              onCreateGroup={() => setPage('create-group')}
            />
          ) : (
            <CreateGroupWizard
              onBack={() => setPage('groups')}
              onComplete={handleCreateGroupComplete}
            />
          )}
        </div>
      </div>
    </div>
  );
}
