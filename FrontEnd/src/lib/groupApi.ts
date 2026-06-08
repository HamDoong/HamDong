import { apiRequest } from './api';

export interface BackendGroup {
  id: number | string;
  name: string;
  description?: string;
  member_count?: number;
  members_count?: number;
  members?: unknown[];
  is_archived?: boolean;
  created_at?: string;
}

export interface CreateGroupInput {
  name: string;
  description?: string;
}

function unwrapList<T>(data: T[] | { results?: T[]; data?: T[] }) {
  if (Array.isArray(data)) return data;
  return data.results || data.data || [];
}

export async function getMyGroups() {
  const data = await apiRequest<BackendGroup[] | { results?: BackendGroup[]; data?: BackendGroup[] }>(
    '/groups/mine/',
  );

  return unwrapList(data);
}

export async function createGroup(input: CreateGroupInput) {
  return apiRequest<BackendGroup>('/groups/', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}