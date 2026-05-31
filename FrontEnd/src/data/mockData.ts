import {
  Building2,
  CheckCircle2,
  Home,
  LogOut,
  Settings,
  TrendingUp,
  User,
  Users,
  UtensilsCrossed,
  Wallet,
} from 'lucide-react';
import type { Activity, Group, Member, NavItem, SummaryItem } from '../types';

export const primaryNavItems: NavItem[] = [
  { id: 'dashboard', label: 'داشبورد', icon: Home },
  { id: 'groups', label: 'گروه‌ها', icon: Users, active: true },
  { id: 'activity', label: 'فعالیت‌ها', icon: TrendingUp },
  { id: 'wallet', label: 'کیف پول', icon: Wallet },
  { id: 'profile', label: 'پروفایل', icon: User },
];

export const secondaryNavItems: NavItem[] = [
  { id: 'settings', label: 'تنظیمات', icon: Settings },
  { id: 'logout', label: 'خروج', icon: LogOut },
];

export const groups: Group[] = [
  {
    id: 1,
    name: 'کافه دوستان',
    membersLabel: '۶ عضو • فعال',
    statusLabel: 'شما طلبکار هستید',
    amount: '+34,250 تومان',
    tone: 'positive',
    illustration: 'cafe',
  },
  {
    id: 2,
    name: 'خانه ما',
    membersLabel: '۴ عضو • فعال',
    statusLabel: 'شما بدهکار هستید',
    amount: '-75,600 تومان',
    tone: 'negative',
    illustration: 'home',
  },
  {
    id: 3,
    name: 'سفر کیش',
    membersLabel: '۵ عضو • فعال',
    statusLabel: 'شما طلبکار هستید',
    amount: '+120,000 تومان',
    tone: 'positive',
    illustration: 'trip',
  },
];

export const accountSummary: SummaryItem[] = [
  { id: 1, label: 'موجودی کیف پول', amount: '+120,000 تومان', tone: 'positive' },
  { id: 2, label: 'شما طلبکار هستید', amount: '+175,000 تومان', tone: 'positive' },
  { id: 3, label: 'شما بدهکار هستید', amount: '-50,000 تومان', tone: 'negative' },
];

export const recentMembers: Member[] = [
  {
    id: 1,
    name: 'علی احمدی (شما)',
    badge: 'مدیر',
    amount: '+۳۵,۰۰۰ تومان',
    tone: 'positive',
    avatarInitial: 'ع',
    avatarGradient: 'from-emerald-400 to-teal-600',
  },
  {
    id: 2,
    name: 'سارا محمدی',
    amount: '-۵۰,۰۰۰',
    tone: 'negative',
    avatarInitial: 'س',
    avatarGradient: 'from-rose-300 to-pink-500',
  },
  {
    id: 3,
    name: 'رضا کریمی',
    amount: '-۶۰,۰۰۰',
    tone: 'negative',
    avatarInitial: 'ر',
    avatarGradient: 'from-amber-300 to-orange-500',
  },
  {
    id: 4,
    name: 'مینا حسینی',
    amount: '+۷۰,۰۰۰',
    tone: 'positive',
    avatarInitial: 'م',
    avatarGradient: 'from-sky-300 to-cyan-500',
  },
  {
    id: 5,
    name: 'حامد نوروزی',
    amount: '-۸۰,۰۰۰',
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
    title: 'رضا مبلغ ۶۰,۰۰۰ تومان پرداخت کرد',
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
