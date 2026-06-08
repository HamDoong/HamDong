import { apiRequest } from './api';

export type BackendGroupType = 'GENERAL' | 'EVENT';

export interface BackendGroup {
  id: string;
  title: string;
  description?: string;
  group_type?: BackendGroupType;
  status?: string;
  created_by_user_id?: string;
  member_count?: number;
  members_count?: number;
  members?: unknown[];
  my_role?: string;
  created_at?: string;
}

export interface CreateGroupInput {
  title: string;
  description?: string;
  group_type?: BackendGroupType;
}

function unwrapList<T>(data: T[] | { results?: T[]; data?: T[] }) {
  if (Array.isArray(data)) return data;
  return data.results || data.data || [];
}

export async function getMyGroups() {
  const data = await apiRequest<
    BackendGroup[] | { results?: BackendGroup[]; data?: BackendGroup[] }
  >('/groups/');

  return unwrapList(data);
}

export async function createGroup(input: CreateGroupInput) {
  return apiRequest<BackendGroup>('/groups/', {
    method: 'POST',
    body: JSON.stringify({
      title: input.title.trim(),
      description: input.description?.trim() || '',
      group_type: input.group_type || 'GENERAL',
    }),
  });
}