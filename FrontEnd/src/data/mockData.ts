import {
  BedDouble,
  Bell,
  Building2,
  CheckCircle2,
  Home,
  LogOut,
  Soup,
  TrendingUp,
  User,
  Users,
  UtensilsCrossed,
  Wallet,
  BriefcaseBusiness,
} from 'lucide-react';
import type {
  Activity,
  Contact,
  Group,
  GroupTypeOptionItem,
  Member,
  NavItem,
  SummaryItem,
} from '../types';

export const primaryNavItems: NavItem[] = [
  { id: 'dashboard', label: 'داشبورد', icon: Home },
  { id: 'groups', label: 'گروه‌ها', icon: Users },
  { id: 'activity', label: 'فعالیت‌ها', icon: TrendingUp },
  { id: 'wallet', label: 'کیف پول', icon: Wallet },
  { id: 'notifications', label: 'اعلان‌ها', icon: Bell },
  { id: 'profile', label: 'حساب کاربری', icon: User },
];

export const secondaryNavItems: NavItem[] = [
  { id: 'logout', label: 'خروج', icon: LogOut },
];

export const groups: Group[] = [
  {
    id: 1,
    name: 'کافه دوستان',
    membersLabel: '۶ عضو • فعال',
    statusLabel: 'شما طلبکار هستید',
    amount: 'تومان 34,250',
    tone: 'positive',
    illustration: 'cafe',
  },
  {
    id: 2,
    name: 'خانه ما',
    membersLabel: '۴ عضو • فعال',
    statusLabel: 'شما بدهکار هستید',
    amount: 'تومان 75,600',
    tone: 'negative',
    illustration: 'home',
  },
  {
    id: 3,
    name: 'سفر کیش',
    membersLabel: '۵ عضو • فعال',
    statusLabel: 'شما طلبکار هستید',
    amount: 'تومان 120,000',
    tone: 'positive',
    illustration: 'trip',
  },
];

export const accountSummary: SummaryItem[] = [
  { id: 1, label: 'موجودی کیف پول', amount: 'تومان 120,000', tone: 'positive' },
  { id: 2, label: 'شما طلبکار هستید', amount: 'تومان 175,000', tone: 'positive' },
  { id: 3, label: 'شما بدهکار هستید', amount: 'تومان 50,000', tone: 'negative' },
];

export const recentMembers: Member[] = [
  {
    id: 1,
    name: 'علی احمدی (شما)',
    badge: 'مدیر',
    amount: 'تومان ۳۵,۰۰۰',
    tone: 'positive',
    avatarInitial: 'ع',
    avatarGradient: 'from-emerald-400 to-teal-600',
  },
  {
    id: 2,
    name: 'سارا محمدی',
    amount: '۵۰,۰۰۰',
    tone: 'negative',
    avatarInitial: 'س',
    avatarGradient: 'from-rose-300 to-pink-500',
  },
  {
    id: 3,
    name: 'رضا کریمی',
    amount: '۶۰,۰۰۰',
    tone: 'negative',
    avatarInitial: 'ر',
    avatarGradient: 'from-amber-300 to-orange-500',
  },
  {
    id: 4,
    name: 'مینا حسینی',
    amount: '۷۰,۰۰۰',
    tone: 'positive',
    avatarInitial: 'م',
    avatarGradient: 'from-sky-300 to-cyan-500',
  },
  {
    id: 5,
    name: 'حامد نوروزی',
    amount: '۸۰,۰۰۰',
    tone: 'negative',
    avatarInitial: 'ح',
    avatarGradient: 'from-slate-400 to-slate-600',
  },
];

export const recentActivities: Activity[] = [
  {
    id: 1,
    title: 'سارا هزینه رستوران را ثبت کرد',
    subtitle: 'کافه دوستان • ۲ ساعت پیش',
    icon: UtensilsCrossed,
    iconBoxClassName: 'bg-violet-100',
    iconClassName: 'text-violet-600',
  },
  {
    id: 2,
    title: 'رضا مبلغ تومان ۶۰,۰۰۰ پرداخت کرد',
    subtitle: 'جلسه ما دیروز',
    icon: CheckCircle2,
    iconBoxClassName: 'bg-emerald-100',
    iconClassName: 'text-emerald-600',
  },
  {
    id: 3,
    title: 'علی هزینه هتل را ثبت کرد',
    subtitle: 'سفر کیش • ۲ روز پیش',
    icon: Building2,
    iconBoxClassName: 'bg-sky-100',
    iconClassName: 'text-sky-600',
  },
];

export const createGroupTypeOptions: GroupTypeOptionItem[] = [
  { value: 'trip', label: 'سفر', icon: BriefcaseBusiness },
  { value: 'food', label: 'غذا و رستوران', icon: Soup },
  { value: 'home', label: 'خانه و زندگی', icon: BedDouble },
  { value: 'other', label: 'سایر', icon: Building2 },
];

export const createGroupContacts: Contact[] = [
  {
    id: 1,
    name: 'علی احمدی',
    phone: '0912 345 6781',
    category: 'friends',
    avatarInitial: 'ع',
    avatarGradient: 'from-emerald-400 to-teal-600',
    isSelf: true,
  },
  {
    id: 2,
    name: 'سارا محمدی',
    phone: '0913 222 3344',
    category: 'friends',
    avatarInitial: 'س',
    avatarGradient: 'from-rose-300 to-pink-500',
  },
  {
    id: 3,
    name: 'رضا کریمی',
    phone: '0914 555 6677',
    category: 'friends',
    avatarInitial: 'ر',
    avatarGradient: 'from-amber-300 to-orange-500',
  },
  {
    id: 4,
    name: 'مینا حسینی',
    phone: '0915 888 9900',
    category: 'friends',
    avatarInitial: 'م',
    avatarGradient: 'from-sky-300 to-cyan-500',
  },
  {
    id: 5,
    name: 'حامد نوروزی',
    phone: '0916 111 2233',
    category: 'friends',
    avatarInitial: 'ح',
    avatarGradient: 'from-slate-400 to-slate-600',
  },
  {
    id: 6,
    name: 'نگار عباسی',
    phone: '0917 444 2201',
    category: 'friends',
    avatarInitial: 'ن',
    avatarGradient: 'from-fuchsia-300 to-purple-500',
  },
  {
    id: 7,
    name: 'محمد طاهری',
    phone: '0918 333 5402',
    category: 'friends',
    avatarInitial: 'م',
    avatarGradient: 'from-cyan-400 to-blue-500',
  },
  {
    id: 8,
    name: 'زهرا قربانی',
    phone: '0919 777 8931',
    category: 'friends',
    avatarInitial: 'ز',
    avatarGradient: 'from-orange-300 to-rose-500',
  },
  {
    id: 9,
    name: 'آرمان عبدی',
    phone: '0920 234 7733',
    category: 'frequent',
    avatarInitial: 'آ',
    avatarGradient: 'from-violet-300 to-indigo-500',
  },
  {
    id: 10,
    name: 'مهسا راد',
    phone: '0921 643 9100',
    category: 'frequent',
    avatarInitial: 'م',
    avatarGradient: 'from-pink-300 to-rose-500',
  },
  {
    id: 11,
    name: 'امیر رضایی',
    phone: '0922 451 6700',
    category: 'frequent',
    avatarInitial: 'ا',
    avatarGradient: 'from-emerald-300 to-lime-500',
  },
  {
    id: 12,
    name: 'پریسا نجفی',
    phone: '0923 990 1144',
    category: 'frequent',
    avatarInitial: 'پ',
    avatarGradient: 'from-teal-300 to-cyan-500',
  },
];
