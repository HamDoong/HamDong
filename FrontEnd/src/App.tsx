import { useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from 'react-router-dom';
import { FeedbackProvider, useFeedback } from './components/feedback/FeedbackProvider';
import { MobileDrawer } from './components/MobileDrawer';
import { Sidebar } from './components/Sidebar';
import { ThemeProvider } from './components/theme/ThemeProvider';
import { TopBar } from './components/TopBar';
import { groups as mockGroups } from './data/mockData';
import { logoutCurrentUser } from './lib/authApi';
import { getAccessToken, getRefreshToken } from './lib/api';
import { listGroupExpenses, type BackendExpense } from './lib/expenseApi';
import {
  archiveGroup,
  createGroup,
  extractInviteToken,
  getBackendGroupMemberEmail,
  getBackendGroupMemberPhone,
  getBackendGroupMemberUserId,
  getGroupDetail,
  getGroupMembers,
  getMyGroups,
  type BackendGroup,
  type BackendGroupType,
} from './lib/groupApi';
import { getPendingNotificationCount } from './lib/notificationApi';
import { getMyGroupBalance } from './lib/settlementApi';
import { getCurrentUser, type CurrentUser } from './lib/userApi';
import { ActivitiesPage } from './pages/ActivitiesPage';
import {
  CreateGroupWizard,
  type CreatedGroupPayload,
} from './pages/CreateGroupWizard';
import { DashboardPage } from './pages/DashboardPage';
import { GroupDetailPage } from './pages/GroupDetailPage';
import { GroupsPage, type GroupBalanceSummary } from './pages/GroupsPage';
import { InviteJoinPage } from './pages/InviteJoinPage';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { NotificationsPage } from './pages/NotificationsPage';
import { ProfilePage } from './pages/ProfilePage';
import { SignUpPage } from './pages/SignUpPage';
import { WalletPage } from './pages/WalletPage';
import type { Group } from './types';

type AppPage = 'dashboard' | 'groups' | 'create-group' | 'group-detail' | 'invite-join' | 'activities' | 'wallet' | 'notifications' | 'profile';
type DashboardGroup = Group;

function getExpenseTotal(expense: BackendExpense) {
  return (
    expense.total_amount_minor ??
    (expense.base_amount_minor || 0) +
      (expense.tax_amount_minor || 0) +
      (expense.service_fee_amount_minor || 0)
  );
}

function getParticipantShare(participant: NonNullable<BackendExpense['participants']>[number]) {
  return (
    participant.total_share_minor ??
    (participant.base_share_minor || 0) +
      (participant.tax_share_minor || 0) +
      (participant.service_fee_share_minor || 0)
  );
}

function formatCardMoney(minor = 0) {
  const sign = minor > 0 ? '+' : minor < 0 ? '-' : '';
  return `${sign}${Math.abs(Math.round(minor)).toLocaleString('fa-IR')} تومان`;
}

function getIllustrationFromBackendGroup(group: BackendGroup): DashboardGroup['illustration'] {
  if (group.group_type === 'EVENT') return 'trip';

  const title = group.title || '';

  if (title.includes('خانه')) return 'home';
  if (title.includes('سفر')) return 'trip';

  return 'cafe';
}

function mapBackendGroupToDashboardGroup(
  group: BackendGroup,
  balance?: GroupBalanceSummary,
): DashboardGroup {
  const baseGroup = mockGroups[0]!;

  const memberCount =
    group.member_count ??
    group.members_count ??
    group.members?.length ??
    1;

  const netMinor = balance?.netMinor ?? 0;
  const balanceLabel =
    netMinor < 0
      ? 'شما بدهکار هستید'
      : netMinor > 0
        ? 'شما طلبکار هستید'
        : group.my_role
          ? `نقش شما: ${group.my_role}`
          : 'تسویه';

  return {
    ...baseGroup,
    id: group.id,
    name: group.title,
    membersLabel: `${memberCount.toLocaleString('fa-IR')} عضو • ${
      group.status === 'ARCHIVED' ? 'آرشیو شده' : 'فعال'
    }`,
    statusLabel: balanceLabel,
    amount: formatCardMoney(netMinor),
    tone: netMinor < 0 ? 'negative' : 'positive',
    illustration: getIllustrationFromBackendGroup(group),
    status: group.status,
    role: group.my_role,
    description: group.description,
  };
}

function normalizeLookupValue(value?: string | null) {
  return (value || '').trim().replace(/\s+/g, '').toLowerCase();
}

function countPersistedSelectedMembers(
  selectedMembers: CreatedGroupPayload,
  persistedMembers: Awaited<ReturnType<typeof getGroupMembers>>,
) {
  const selectedUserIds = new Set(
    (selectedMembers.selectedUserIds || []).map((value) => normalizeLookupValue(value)).filter(Boolean),
  );
  const selectedPhones = new Set(
    (selectedMembers.selectedPhones || []).map((value) => normalizeLookupValue(value)).filter(Boolean),
  );
  const selectedEmails = new Set(
    (selectedMembers.selectedEmails || []).map((value) => normalizeLookupValue(value)).filter(Boolean),
  );

  if (!selectedUserIds.size && !selectedPhones.size && !selectedEmails.size) {
    return 0;
  }

  return persistedMembers.filter((member) => {
    const memberUserId = normalizeLookupValue(getBackendGroupMemberUserId(member));
    const memberPhone = normalizeLookupValue(getBackendGroupMemberPhone(member));
    const memberEmail = normalizeLookupValue(getBackendGroupMemberEmail(member));

    return (
      (memberUserId && selectedUserIds.has(memberUserId)) ||
      (memberPhone && selectedPhones.has(memberPhone)) ||
      (memberEmail && selectedEmails.has(memberEmail))
    );
  }).length;
}


function getUserShareForExpense(expense: BackendExpense, userId: string, memberCount = 1) {
  if (expense.participants?.length) {
    const participant = expense.participants.find((item) => item.user_id === userId);
    return participant ? getParticipantShare(participant) : 0;
  }

  const safeMemberCount = Math.max(memberCount, 1);
  return Math.round(getExpenseTotal(expense) / safeMemberCount);
}

async function buildGroupBalanceSummary(
  group: BackendGroup,
  currentUser: CurrentUser | null,
): Promise<GroupBalanceSummary> {
  const userId = currentUser?.id ? String(currentUser.id) : '';

  try {
    const balance = await getMyGroupBalance(group.id);
    const netMinor = balance.net_balance_minor || 0;

    return {
      groupId: group.id,
      groupName: group.title,
      status: group.status,
      paidMinor: netMinor > 0 ? netMinor : 0,
      shareMinor: netMinor < 0 ? Math.abs(netMinor) : 0,
      netMinor,
    };
  } catch (error) {
    console.warn(`Could not load settlement balance for group ${group.id}. Falling back to expense math.`, error);
  }

  const expenses = await listGroupExpenses(group.id, { page_size: 100 }).catch(() => []);
  const activeExpenses = expenses.filter(
    (expense) => expense.status !== 'DELETED' && expense.status !== 'CANCELLED',
  );

  const paidMinor = activeExpenses.reduce((sum, expense) => {
    return expense.payer_user_id === userId ? sum + getExpenseTotal(expense) : sum;
  }, 0);

  const memberCount = group.member_count ?? group.members_count ?? group.members?.length ?? 1;
  const shareMinor = userId
    ? activeExpenses.reduce((sum, expense) => {
        return sum + getUserShareForExpense(expense, userId, memberCount);
      }, 0)
    : 0;

  return {
    groupId: group.id,
    groupName: group.title,
    status: group.status,
    paidMinor,
    shareMinor,
    netMinor: paidMinor - shareMinor,
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
  if (page === 'dashboard') return 'dashboard';
  if (page === 'activities') return 'activities';
  if (page === 'wallet') return 'wallet';
  if (page === 'notifications') return 'notifications';
  if (page === 'profile') return 'profile';
  return 'groups';
}

function getPageFromHash(): Extract<AppPage, 'dashboard' | 'groups' | 'activities' | 'wallet' | 'notifications' | 'profile'> {
  const hash = window.location.hash.replace('#', '');

  if (hash === 'groups') return 'groups';
  if (hash === 'activities') return 'activities';
  if (hash === 'wallet') return 'wallet';
  if (hash === 'notifications') return 'notifications';
  if (hash === 'profile') return 'profile';

  return 'dashboard';
}

function AppContent() {
  const navigate = useNavigate();
  const { notify, confirm } = useFeedback();
  const initialInviteToken = useMemo(() => getInviteTokenFromLocation(), []);

  const [page, setPage] = useState<AppPage>(initialInviteToken ? 'invite-join' : getPageFromHash());
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);
  const [groupItems, setGroupItems] = useState<DashboardGroup[]>([]);
  const [groupBalances, setGroupBalances] = useState<GroupBalanceSummary[]>([]);
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null);
  const [inviteToken, setInviteToken] = useState(initialInviteToken);

  const [loadingGroups, setLoadingGroups] = useState(false);
  const [balancesLoading, setBalancesLoading] = useState(false);
  const [groupsError, setGroupsError] = useState<string | null>(null);
  const [currentUserDisplayName, setCurrentUserDisplayName] = useState('کاربر');
  const [notificationBadgeCount, setNotificationBadgeCount] = useState(0);

  async function loadInitialData() {
    let backendGroups: BackendGroup[] = [];
    let currentUser: CurrentUser | null = null;

    try {
      setLoadingGroups(true);
      setGroupsError(null);

      backendGroups = await getMyGroups();
      setGroupItems(backendGroups.map((group) => mapBackendGroupToDashboardGroup(group)));
    } catch (error) {
      console.error(error);
      setGroupsError('فعلاً گروه‌ها بارگذاری نشدند. دوباره تلاش کن.');
    } finally {
      setLoadingGroups(false);
    }

    try {
      currentUser = await getCurrentUser();

      const displayName =
        currentUser.art_name ||
        currentUser.display_name ||
        currentUser.phone ||
        currentUser.username ||
        currentUser.phone_number ||
        'کاربر';

      setCurrentUserDisplayName(displayName);
    } catch (error) {
      console.warn('Could not load current user profile. Keeping fallback display name.', error);
    }

    if (backendGroups.length > 0) {
      try {
        setBalancesLoading(true);
        const summaries = await Promise.all(
          backendGroups.map((group) => buildGroupBalanceSummary(group, currentUser)),
        );

        const summaryMap = new Map(summaries.map((item) => [item.groupId, item]));
        setGroupBalances(summaries);
        setGroupItems(backendGroups.map((group) => mapBackendGroupToDashboardGroup(group, summaryMap.get(group.id))));
      } finally {
        setBalancesLoading(false);
      }
    } else {
      setGroupBalances([]);
    }
  }

  async function loadNotificationBadge() {
    const count = await getPendingNotificationCount();
    setNotificationBadgeCount(count);
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
    loadNotificationBadge();
  }, []);

  useEffect(() => {
    const handlePopState = () => {
      const tokenFromUrl = getInviteTokenFromLocation();

      if (tokenFromUrl) {
        setInviteToken(tokenFromUrl);
        setPage('invite-join');
        setSelectedGroupId(null);
      } else {
        setPage(getPageFromHash());
        setInviteToken('');
      }
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const handleLogout = async () => {
    await logoutCurrentUser();
    setGroupItems([]);
    setGroupBalances([]);
    setSelectedGroupId(null);
    setInviteToken('');
    setNotificationBadgeCount(0);
    setCurrentUserDisplayName('کاربر');
    navigate('/', { replace: true });
  };

  const handleSidebarNavigate = (itemId: string) => {
    if (itemId === 'logout') {
      void handleLogout();
      return;
    }

    if (itemId === 'dashboard') {
      setSelectedGroupId(null);
      setInviteToken('');
      setPage('dashboard');
      setBrowserPath('/Dashboard');
      loadInitialData();
      return;
    }

    if (itemId === 'groups') {
      setSelectedGroupId(null);
      setInviteToken('');
      setPage('groups');
      setBrowserPath('/Dashboard#groups');
      loadInitialData();
      return;
    }

    if (itemId === 'activity' || itemId === 'activities') {
      setSelectedGroupId(null);
      setInviteToken('');
      setPage('activities');
      setBrowserPath('/Dashboard#activities');
      return;
    }

    if (itemId === 'wallet') {
      setSelectedGroupId(null);
      setInviteToken('');
      setPage('wallet');
      setBrowserPath('/Dashboard#wallet');
      return;
    }

    if (itemId === 'notifications') {
      setSelectedGroupId(null);
      setInviteToken('');
      setPage('notifications');
      setBrowserPath('/Dashboard#notifications');
      return;
    }

    if (itemId === 'profile') {
      setSelectedGroupId(null);
      setInviteToken('');
      setPage('profile');
      setBrowserPath('/Dashboard#profile');
      return;
    }

    notify({
      type: 'info',
      title: 'این بخش هنوز آماده نشده',
      description: 'این بخش هنوز در حال تکمیل است و به‌زودی اضافه می‌شود.',
    });
  };

  const handleOpenNotifications = () => {
    setSelectedGroupId(null);
    setInviteToken('');
    setPage('notifications');
    setBrowserPath('/Dashboard#notifications');
  };

  const handleCreateGroupComplete = async (payload: CreatedGroupPayload) => {
    try {
      const backendGroup = await createGroup({
        title: payload.name || 'گروه جدید',
        description: payload.description || '',
        group_type: mapWizardGroupTypeToBackendType(payload.groupType),
        member_user_ids: payload.selectedUserIds,
        member_emails: payload.selectedEmails,
        member_phones: payload.selectedPhones,
      });

      const mappedGroup = mapBackendGroupToDashboardGroup(backendGroup);

      setGroupItems((prev) => [mappedGroup, ...prev]);
      setGroupBalances((prev) => [
        {
          groupId: backendGroup.id,
          groupName: backendGroup.title,
          status: backendGroup.status,
          paidMinor: 0,
          shareMinor: 0,
          netMinor: 0,
        },
        ...prev,
      ]);

      setSelectedGroupId(backendGroup.id);
      setPage('group-detail');
      setBrowserPath('/Dashboard#groups');

      let persistedSelectedMembers = 0;

      if (
        (payload.selectedUserIds?.length || 0) > 0 ||
        (payload.selectedPhones?.length || 0) > 0 ||
        (payload.selectedEmails?.length || 0) > 0
      ) {
        try {
          const persistedMembers = await getGroupMembers(backendGroup.id);
          persistedSelectedMembers = countPersistedSelectedMembers(payload, persistedMembers);
        } catch (error) {
          console.warn('Could not verify created group members.', error);
        }
      }

      try {
        const refreshedGroup = await getGroupDetail(backendGroup.id);
        handleGroupUpdated(refreshedGroup);
      } catch (error) {
        console.warn('Could not refresh created group detail.', error);
      }

      notify({
        type: persistedSelectedMembers < payload.memberCount ? 'info' : 'success',
        title: persistedSelectedMembers < payload.memberCount ? 'گروه ساخته شد' : 'گروه ساخته شد',
        description:
          persistedSelectedMembers < payload.memberCount && payload.memberCount > 0
            ? 'گروه ساخته شد، اما سرویس گروه هنوز همه اعضای انتخاب‌شده را مستقیم برنگرداند. اگر لازم بود از لینک دعوت داخل جزئیات گروه استفاده کن.'
            : 'حالا می‌تونی اعضا، دعوت‌ها و تنظیمات گروه را مدیریت کنی.',
      });
    } catch (error) {
      console.error(error);
      notify({
        type: 'error',
        title: 'ایجاد گروه ناموفق بود',
        description: 'گروه ساخته نشد. دوباره تلاش کن.',
      });
    }
  };

  const handleOpenGroup = (groupId: string) => {
    setSelectedGroupId(groupId);
    setPage('group-detail');
    setBrowserPath('/Dashboard#groups');
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

  const handleDeleteGroupFromCard = async (group: Group) => {
    if (group.status === 'ARCHIVED') {
      notify({
        type: 'info',
        title: 'این گروه قبلاً آرشیو شده',
        description: 'گروه‌های آرشیو شده از لیست فعال‌ها جدا شده‌اند.',
      });
      return;
    }

    const confirmed = await confirm({
      title: 'حذف گروه از لیست فعال‌ها؟',
      description: 'این عملیات گروه را از لیست گروه‌های فعال حذف می‌کند و به بخش گروه‌های آرشیو شده منتقل می‌کند.',
      confirmText: 'حذف از لیست',
      cancelText: 'انصراف',
      tone: 'danger',
    });

    if (!confirmed) return;

    try {
      await archiveGroup(String(group.id));

      try {
        const refreshedGroup = await getGroupDetail(String(group.id));
        handleGroupUpdated(refreshedGroup);
      } catch {
        setGroupItems((prev) =>
          prev.map((item) =>
            String(item.id) === String(group.id)
              ? {
                  ...item,
                  status: 'ARCHIVED',
                  membersLabel: item.membersLabel.replace('فعال', 'آرشیو شده'),
                }
              : item,
          ),
        );
        setGroupBalances((prev) =>
          prev.map((item) =>
            item.groupId === String(group.id) ? { ...item, status: 'ARCHIVED' } : item,
          ),
        );
      }

      notify({
        type: 'success',
        title: 'گروه حذف شد',
        description: 'گروه از لیست فعال‌ها حذف شد و در آرشیو قرار گرفت.',
      });
    } catch (error) {
      console.error(error);
      notify({
        type: 'error',
        title: 'حذف گروه ناموفق بود',
        description: 'گروه ساخته نشد. دوباره تلاش کن.',
      });
    }
  };

  const handleBackToGroups = () => {
    setSelectedGroupId(null);
    setInviteToken('');
    setPage('groups');
    setBrowserPath('/Dashboard#groups');
    loadInitialData();
  };

  const handleInviteAccepted = async () => {
    setInviteToken('');
    setPage('groups');
    setBrowserPath('/Dashboard#groups');
    await loadInitialData();
  };

  const handleGroupUpdated = (group: BackendGroup) => {
    setGroupBalances((prev) =>
      prev.map((item) =>
        item.groupId === group.id
          ? {
              ...item,
              groupName: group.title,
              status: group.status,
            }
          : item,
      ),
    );

    setGroupItems((prev) => {
      const balance = groupBalances.find((item) => item.groupId === group.id);
      const mappedGroup = mapBackendGroupToDashboardGroup(group, balance);
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
    setGroupBalances((prev) => prev.filter((item) => item.groupId !== groupId));
    setSelectedGroupId(null);
    setPage('groups');
    setBrowserPath('/Dashboard#groups');
  };

  const handleOpenGroupsPage = () => {
    setSelectedGroupId(null);
    setInviteToken('');
    setPage('groups');
    setBrowserPath('/Dashboard#groups');
  };

  const handleOpenActivitiesPage = () => {
    setSelectedGroupId(null);
    setInviteToken('');
    setPage('activities');
    setBrowserPath('/Dashboard#activities');
  };

  const handleOpenWalletPage = () => {
    setSelectedGroupId(null);
    setInviteToken('');
    setPage('wallet');
    setBrowserPath('/Dashboard#wallet');
  };

  return (
    <div dir="rtl" className="app-auth-background min-h-screen text-text">
      <MobileDrawer open={mobileDrawerOpen} onClose={() => setMobileDrawerOpen(false)} activePage={getSidebarActivePage(page)} onNavigate={handleSidebarNavigate} />

      <div className="min-h-screen w-full lg:relative lg:pr-[236px] 2xl:pr-[252px]">
        <Sidebar className="hidden lg:fixed lg:right-0 lg:top-0 lg:z-30 lg:flex lg:h-screen lg:w-[236px] lg:shrink-0 lg:border-l lg:border-border/90 2xl:w-[252px]" activePage={getSidebarActivePage(page)} onNavigate={handleSidebarNavigate} />

        <div className="min-w-0">
          <TopBar
            onMenuClick={() => setMobileDrawerOpen(true)}
            displayName={currentUserDisplayName}
            unreadNotificationCount={notificationBadgeCount}
            onOpenNotifications={handleOpenNotifications}
            groups={groupItems.map((group) => ({
              id: String(group.id),
              name: group.name,
            }))}
            onOpenGroup={handleOpenGroup}
          />

          {page === 'dashboard' ? (
            <DashboardPage
              groups={groupItems}
              groupBalances={groupBalances}
              balancesLoading={balancesLoading}
              groupsLoading={loadingGroups}
              groupsError={groupsError}
              onCreateGroup={() => setPage('create-group')}
              onOpenGroups={handleOpenGroupsPage}
              onOpenGroup={handleOpenGroup}
              onOpenActivities={handleOpenActivitiesPage}
              onOpenWallet={handleOpenWalletPage}
            />
          ) : null}

          {page === 'groups' ? (
            <GroupsPage
              groups={groupItems}
              groupBalances={groupBalances}
              balancesLoading={balancesLoading}
              loading={loadingGroups}
              error={groupsError}
              onCreateGroup={() => setPage('create-group')}
              onOpenGroup={handleOpenGroup}
              onOpenInvite={handleOpenInvite}
              onDeleteGroup={handleDeleteGroupFromCard}
            />
          ) : null}

          {page === 'activities' ? <ActivitiesPage /> : null}
          {page === 'wallet' ? (
            <WalletPage
              onOpenActivities={handleOpenActivitiesPage}
              onOpenGroups={handleOpenGroupsPage}
            />
          ) : null}
          {page === 'notifications' ? (
            <NotificationsPage onUnreadCountChange={setNotificationBadgeCount} />
          ) : null}
          {page === 'profile' ? <ProfilePage /> : null}

          {page === 'create-group' ? (
            <CreateGroupWizard onBack={() => setPage('groups')} onComplete={handleCreateGroupComplete} />
          ) : null}

          {page === 'group-detail' && selectedGroupId ? (
            <GroupDetailPage groupId={selectedGroupId} onBack={handleBackToGroups} onGroupUpdated={handleGroupUpdated} onGroupRemoved={handleGroupRemoved} />
          ) : null}

          {page === 'invite-join' ? (
            <InviteJoinPage initialToken={inviteToken} onBack={handleBackToGroups} onAccepted={handleInviteAccepted} />
          ) : null}
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <FeedbackProvider>
          <AppRoutes />
        </FeedbackProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}

function AuthPageFrame({
  children,
  className = '',
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div dir="rtl" className={`min-h-screen text-text ${className}`.trim()}>
      {children}
    </div>
  );
}

function ProtectedRoute({ children }: { children: ReactNode }) {
  const location = useLocation();
  const hasAuthToken = Boolean(getAccessToken() || getRefreshToken());

  if (!hasAuthToken) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <>{children}</>;
}

function AppRoutes() {
  const navigate = useNavigate();

  return (
    <Routes>
      <Route
        path="/"
        element={
          <AuthPageFrame className="bg-background">
            <LandingPage />
          </AuthPageFrame>
        }
      />
      <Route
        path="/login"
        element={
          <AuthPageFrame className="auth-page-background">
            <LoginPage
              onLogin={() => navigate('/Dashboard', { replace: true })}
              onSignUp={() => navigate('/signup')}
              onLanding={() => navigate('/')}
            />
          </AuthPageFrame>
        }
      />
      <Route
        path="/signup"
        element={
          <AuthPageFrame className="auth-page-background">
            <SignUpPage
              onLogin={() => navigate('/login')}
              onSignUp={() => navigate('/Dashboard', { replace: true })}
              onLanding={() => navigate('/')}
            />
          </AuthPageFrame>
        }
      />
      <Route
        path="/Dashboard/*"
        element={
          <ProtectedRoute>
            <AppContent />
          </ProtectedRoute>
        }
      />
      <Route path="/landing" element={<Navigate to="/" replace />} />
      <Route path="/invites/:token" element={<AppContent />} />
      <Route path="/groups/*" element={<Navigate to="/Dashboard#groups" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
