import type { LucideIcon } from 'lucide-react';

export type BalanceTone = 'positive' | 'negative';
export type GroupIllustrationType = 'trip' | 'home' | 'cafe';
export type GroupTypeOption = 'trip' | 'food' | 'home' | 'other';
export type ContactCategory = 'friends' | 'frequent';
export type CreateGroupStep = 1 | 2 | 3;

export interface NavItem {
  id: string;
  label: string;
  icon: LucideIcon;
  active?: boolean;
}

export interface Group {
  id: string | number;
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

export interface Contact {
  id: number;
  name: string;
  phone: string;
  category: ContactCategory;
  avatarInitial: string;
  avatarGradient: string;
  isSelf?: boolean;
}

export interface GroupTypeOptionItem {
  value: GroupTypeOption;
  label: string;
  icon: LucideIcon;
}

export interface CreateGroupDraft {
  name: string;
  type: GroupTypeOption | '';
  description: string;
  startDate: string;
  currency: string;
  selectedMemberIds: number[];
}
