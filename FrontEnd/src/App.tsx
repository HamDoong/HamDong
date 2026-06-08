import { useEffect, useMemo, useState } from 'react';
import { FeedbackProvider, useFeedback } from './components/feedback/FeedbackProvider';
import { MobileDrawer } from './components/MobileDrawer';
import { Sidebar } from './components/Sidebar';
import { TopBar } from './components/TopBar';
import { groups as mockGroups } from './data/mockData';
import {
  createGroup,
  extractInviteToken,
  getMyGroups,
  type BackendGroup,
  type BackendGroupType,
} from './lib/groupApi';
import { getCurrentUser } from './lib/userApi';
import {
  CreateGroupWizard,
  type CreatedGroupPayload,
} from './pages/CreateGroupWizard';
import { ActivitiesPage } from './pages/ActivitiesPage';
import { GroupDetailPage } from './pages/GroupDetailPage';
import { GroupsPage } from './pages/GroupsPage';
import { InviteJoinPage } from './pages/InviteJoinPage';
import type { Group } from './types';

type AppPage = 'groups' | 'create-group' | 'group-detail' | 'invite-join' | 'activities';
type DashboardGroup = Group;

function getIllustrationFromBackendGroup(group: BackendGroup): DashboardGroup['illustration'] {
  if (group.group_type === 'EVENT') return 'trip';

  const title = group.title || '';

  if (title.includes('خانه')) return 'home';
  if (title.includes('سفر')) return 'trip';

  return 'cafe';
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
    id: group.id,
    name: group.title,
    membersLabel: `${memberCount.toLocaleString('fa-IR')} عضو • ${
      group.status === 'ARCHIVED' ? 'آرشیو شده' : 'فعال'
    }`,
    statusLabel: group.my_role ? `نقش شما: ${group.my_role}` : 'تراز این گروه صفر است',
    amount: '۰ تومان',
    tone: 'positive',
    illustration: getIllustrationFromBackendGroup(group),
    status: group.status,
    role: group.my_role,
    description: group.description,
  };
}

function mapWizardGroupTypeToBackendType(
  groupType: CreatedGroupPayload['groupType'],
): BackendGroupType {
  if (groupType === 'travel') return 'EVENT';
  return 'GENERAL';
}

function getInviteTokenFromLocation() {
  const pathMatch = window.location.pathname.match(/\/invites\/([^/?#]+)/);
  const searchParams = new URLSearchParams(window.location.search);
  const queryToken = searchParams.get('token') || searchParams.get('invite');
  const hashMatch = window.location.hash.match(/\/invites\/([^/?#]+)/);

  return extractInviteToken(pathMatch?.[1] || queryToken || hashMatch?.[1] || '');
}

function setBrowserPath(path: string) {
  window.history.pushState({}, '', path);
}

function getSidebarActivePage(page: AppPage) {
  if (page === 'activities') return 'activities';
  return 'groups';
}

function AppContent() {
  const { notify } = useFeedback();
  const initialInviteToken = useMemo(() => getInviteTokenFromLocation(), []);

  const [page, setPage] = useState<AppPage>(initialInviteToken ? 'invite-join' : 'groups');
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);
  const [groupItems, setGroupItems] = useState<DashboardGroup[]>([]);
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null);
  const [inviteToken, setInviteToken] = useState(initialInviteToken);

  const [loadingGroups, setLoadingGroups] = useState(false);
  const [groupsError, setGroupsError] = useState<string | null>(null);
  const [currentUserPhone, setCurrentUserPhone] = useState('کاربر');

  async function loadInitialData() {
    try {
      setLoadingGroups(true);
      setGroupsError(null);

      const [backendGroups, currentUser] = await Promise.all([
        getMyGroups(),
        getCurrentUser(),
      ]);

      setGroupItems(backendGroups.map(mapBackendGroupToDashboardGroup));

      const phone =
        currentUser.phone_number ||
        currentUser.phone ||
        currentUser.username ||
        'کاربر';

      setCurrentUserPhone(phone);
    } catch (error) {
      console.error(error);
      setGroupsError('خطا در دریافت اطلاعات از بک‌اند');
    } finally {
      setLoadingGroups(false);
    }
  }

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

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    const handlePopState = () => {
      const tokenFromUrl = getInviteTokenFromLocation();

      if (tokenFromUrl) {
        setInviteToken(tokenFromUrl);
        setPage('invite-join');
        setSelectedGroupId(null);
      } else {
        setPage('groups');
        setInviteToken('');
      }
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const handleSidebarNavigate = (itemId: string) => {
    if (itemId === 'groups') {
      setSelectedGroupId(null);
      setInviteToken('');
      setPage('groups');
      setBrowserPath('/Dashboard#');
      loadInitialData();
      return;
    }

    if (itemId === 'activity') {
      setSelectedGroupId(null);
      setInviteToken('');
      setPage('activities');
      setBrowserPath('/Dashboard#activities');
      return;
    }

    notify({
      type: 'info',
      title: 'این بخش هنوز آماده نشده',
      description: 'فعلاً صفحه گروه‌ها و فعالیت‌ها برای UI فعال هستند.',
    });
  };

  const handleCreateGroupComplete = async (payload: CreatedGroupPayload) => {
    try {
      const backendGroup = await createGroup({
        title: payload.name || 'گروه جدید',
        description: payload.description || '',
        group_type: mapWizardGroupTypeToBackendType(payload.groupType),
      });

      setGroupItems((prev) => [
        mapBackendGroupToDashboardGroup(backendGroup),
        ...prev,
      ]);

      setSelectedGroupId(backendGroup.id);
      setPage('group-detail');
      setBrowserPath('/Dashboard#');

      notify({
        type: 'success',
        title: 'گروه ساخته شد',
        description: 'حالا می‌تونی اعضا، دعوت‌ها و تنظیمات گروه را مدیریت کنی.',
      });
    } catch (error) {
      console.error(error);
      notify({
        type: 'error',
        title: 'ایجاد گروه ناموفق بود',
        description: 'Network و Console را بررسی کن.',
      });
    }
  };

  const handleOpenGroup = (groupId: string) => {
    setSelectedGroupId(groupId);
    setPage('group-detail');
    setBrowserPath('/Dashboard#');
  };

  const handleOpenInvite = (tokenOrLink: string) => {
    const token = extractInviteToken(tokenOrLink);

    if (!token) {
      notify({
        type: 'error',
        title: 'لینک دعوت نامعتبر است',
        description: 'لینک یا توکن دعوت را دوباره بررسی کن.',
      });
      return;
    }

    setInviteToken(token);
    setSelectedGroupId(null);
    setPage('invite-join');
    setBrowserPath(`/invites/${encodeURIComponent(token)}`);
  };

  const handleBackToGroups = () => {
    setSelectedGroupId(null);
    setInviteToken('');
    setPage('groups');
    setBrowserPath('/Dashboard#');
    loadInitialData();
  };

  const handleInviteAccepted = async () => {
    setInviteToken('');
    setPage('groups');
    setBrowserPath('/Dashboard#');
    await loadInitialData();
  };

  const handleGroupUpdated = (group: BackendGroup) => {
    setGroupItems((prev) => {
      const mappedGroup = mapBackendGroupToDashboardGroup(group);
      const exists = prev.some((item) => String(item.id) === group.id);

      if (!exists) {
        return [mappedGroup, ...prev];
      }

      return prev.map((item) =>
        String(item.id) === group.id ? mappedGroup : item,
      );
    });
  };

  const handleGroupRemoved = (groupId: string) => {
    setGroupItems((prev) => prev.filter((item) => String(item.id) !== groupId));
    setSelectedGroupId(null);
    setPage('groups');
    setBrowserPath('/Dashboard#');
  };

  return (
    <div dir="rtl" className="min-h-screen bg-background text-text">
      <MobileDrawer
        open={mobileDrawerOpen}
        onClose={() => setMobileDrawerOpen(false)}
        activePage={getSidebarActivePage(page)}
        onNavigate={handleSidebarNavigate}
      />

      <div className="mx-auto min-h-screen max-w-[1536px] lg:grid lg:grid-cols-[236px_minmax(0,1fr)]">
        <Sidebar
          className="hidden lg:flex lg:h-screen lg:w-[236px] lg:shrink-0 lg:border-l lg:border-border/90"
          activePage={getSidebarActivePage(page)}
          onNavigate={handleSidebarNavigate}
        />

        <div className="min-w-0">
          <TopBar
            onMenuClick={() => setMobileDrawerOpen(true)}
            displayName={currentUserPhone}
          />

          {page === 'groups' ? (
            <GroupsPage
              groups={groupItems}
              loading={loadingGroups}
              error={groupsError}
              onCreateGroup={() => setPage('create-group')}
              onOpenGroup={handleOpenGroup}
              onOpenInvite={handleOpenInvite}
            />
          ) : null}

          {page === 'activities' ? <ActivitiesPage /> : null}

          {page === 'create-group' ? (
            <CreateGroupWizard
              onBack={() => setPage('groups')}
              onComplete={handleCreateGroupComplete}
            />
          ) : null}

          {page === 'group-detail' && selectedGroupId ? (
            <GroupDetailPage
              groupId={selectedGroupId}
              onBack={handleBackToGroups}
              onGroupUpdated={handleGroupUpdated}
              onGroupRemoved={handleGroupRemoved}
            />
          ) : null}

          {page === 'invite-join' ? (
            <InviteJoinPage
              initialToken={inviteToken}
              onBack={handleBackToGroups}
              onAccepted={handleInviteAccepted}
            />
          ) : null}
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <FeedbackProvider>
      <AppContent />
    </FeedbackProvider>
  );
}
