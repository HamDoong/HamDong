import type { LucideIcon } from 'lucide-react';

export type BalanceTone = 'positive' | 'negative';
export type GroupIllustrationType = 'trip' | 'home' | 'cafe';

export interface NavItem {
  id: string;
  label: string;
  icon: LucideIcon;
  active?: boolean;
}

export interface Group {
  id: number;
  name: string;
  membersLabel: string;
  statusLabel: string;
  amount: string;
  tone: BalanceTone;
  illustration: GroupIllustrationType;
}

export interface SummaryItem {
  id: number;
  label: string;
  amount: string;
  tone: BalanceTone;
}

export interface Member {
  id: number;
  name: string;
  badge?: string;
  amount: string;
  tone: BalanceTone;
  avatarInitial: string;
  avatarGradient: string;
}

export interface Activity {
  id: number;
  title: string;
  subtitle: string;
  icon: LucideIcon;
  iconBoxClassName: string;
  iconClassName: string;
}
