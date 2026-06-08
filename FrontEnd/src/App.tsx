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
import { createGroup, getMyGroups, type BackendGroup } from './lib/groupApi';

type AppPage = 'groups' | 'create-group';
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
  const [page, setPage] = useState<AppPage>('groups');
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);
  const [groupItems, setGroupItems] = useState<DashboardGroup[]>(mockGroups);
  const [loadingGroups, setLoadingGroups] = useState(false);
  const [groupsError, setGroupsError] = useState<string | null>(null);
  useEffect(() => {
    let ignore = false;

    async function loadGroups() {
      try {
        setLoadingGroups(true);
        setGroupsError(null);

        const backendGroups = await getMyGroups();

        if (!ignore) {
          setGroupItems(backendGroups.map(mapBackendGroupToDashboardGroup));
        }
      } catch (error) {
        console.error(error);

        if (!ignore) {
          setGroupsError('خطا در دریافت گروه‌ها از بک‌اند');
        }
      } finally {
        if (!ignore) {
          setLoadingGroups(false);
        }
      }
    }

    loadGroups();

    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = mobileDrawerOpen ? 'hidden' : originalOverflow;

    return () => {
      document.body.style.overflow = originalOverflow;
    };
  }, [mobileDrawerOpen]);

  const handleCreateGroupComplete = async (payload: CreatedGroupPayload) => {
    try {
      const backendGroup = await createGroup({
        name: payload.name || 'گروه جدید',
        description: '',
      });

      setGroupItems((prev) => [
        mapBackendGroupToDashboardGroup(backendGroup),
        ...prev,
      ]);

      setPage('groups');
    } catch (error) {
      console.error(error);
      alert('ایجاد گروه ناموفق بود. لاگ کنسول را بررسی کن.');
    }
  };
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
              loading={loadingGroups}
              error={groupsError}
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

function mapBackendGroupToDashboardGroup(group: BackendGroup): DashboardGroup {
  const baseGroup = mockGroups[0]!;

  const memberCount =
    group.member_count ??
    group.members_count ??
    group.members?.length ??
    1;

  return {
    ...baseGroup,
    id: Number(group.id),
    name: group.name,
    membersLabel: `${memberCount.toLocaleString('fa-IR')} عضو • ${
      group.is_archived ? 'آرشیو شده' : 'فعال'
    }`,
    statusLabel: 'تراز این گروه صفر است',
    amount: '۰ تومان',
    tone: 'positive',
    illustration: baseGroup.illustration,
  };
}