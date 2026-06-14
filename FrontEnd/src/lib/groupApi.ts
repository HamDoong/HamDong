import { apiRequest } from './api';

export type BackendGroupType = 'GENERAL' | 'EVENT';
export type BackendGroupStatus = 'ACTIVE' | 'ARCHIVED';

export interface BackendGroup {
  id: string;
  title: string;
  description?: string;
  group_type: BackendGroupType;
  status: BackendGroupStatus;
  created_by_user_id?: string;
  member_count?: number;
  members_count?: number;
  members?: unknown[];
  created_at?: string;
  updated_at?: string;
  my_role?: string;
}

export interface BackendGroupMember {
  id?: string;
  member_id?: string;
  user_id?: string;

  art_name?: string;
  username?: string;
  display_name_snapshot?: string | null;
  display_name?: string;
  full_name?: string;
  phone_number?: string;
  phone?: string;
  role?: string;
  joined_at?: string;
}

export interface CreateGroupInput {
  title: string;
  description?: string;
  group_type?: BackendGroupType;
}

export interface UpdateGroupInput {
  title?: string;
  description?: string;
  group_type?: BackendGroupType;
  status?: BackendGroupStatus;
}

export interface CreateInviteInput {
  expires_in_hours?: number;
  max_uses?: number;
}

export interface CreatedInvite {
  id?: string;
  invite_id?: string;
  token?: string;
  invite_token?: string;
  invite_url?: string;
  url?: string;
  expires_at?: string;
  max_uses?: number;
}

export interface InvitePreview {
  group_id?: string;
  group?: {
    id?: string;
    title?: string;
    description?: string;
    group_type?: BackendGroupType;
    status?: BackendGroupStatus;
  };
  title?: string;
  description?: string;
  group_type?: BackendGroupType;
  status?: string;
  expires_at?: string;
  invite_status?: string;
}

function unwrapList<T>(data: T[] | { results?: T[]; data?: T[] }) {
  if (Array.isArray(data)) return data;
  return data.results || data.data || [];
}

function safeDecode(value: string) {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

function extractTokenFromPath(pathname: string) {
  const match = pathname.match(/(?:^|\/)(?:invite|invites)\/([^/?#]+)/i);
  return match?.[1] || '';
}

export function extractInviteToken(value: string) {
  const trimmed = value.trim().replace(/^['"]|['"]$/g, '');

  if (!trimmed) return '';

  try {
    const url = new URL(trimmed);
    const pathToken = extractTokenFromPath(url.pathname);
    const queryToken =
      url.searchParams.get('token') ||
      url.searchParams.get('invite') ||
      url.searchParams.get('invite_token');

    return safeDecode(pathToken || queryToken || '');
  } catch {
    const pathToken = extractTokenFromPath(trimmed);

    if (pathToken) {
      return safeDecode(pathToken);
    }

    const withoutQuery = trimmed.split(/[?#]/)[0];
    const lastSegment = withoutQuery.split('/').filter(Boolean).pop();

    return safeDecode(lastSegment || trimmed);
  }
}

export function getInviteUrl(invite: CreatedInvite) {
  if (invite.invite_url) return invite.invite_url;
  if (invite.url) return invite.url;

  const token = invite.token || invite.invite_token;

  if (token) {
    return `${window.location.origin}/invites/${encodeURIComponent(token)}`;
  }

  return '';
}

export function getInviteId(invite: CreatedInvite) {
  return invite.invite_id || invite.id || '';
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

export async function getGroupDetail(groupId: string) {
  return apiRequest<BackendGroup>(`/groups/${groupId}/`);
}

export async function updateGroup(groupId: string, input: UpdateGroupInput) {
  const body: UpdateGroupInput = {};

  if (typeof input.title === 'string') body.title = input.title.trim();
  if (typeof input.description === 'string') body.description = input.description.trim();
  if (input.group_type) body.group_type = input.group_type;
  if (input.status) body.status = input.status;

  return apiRequest<BackendGroup>(`/groups/${groupId}/`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  });
}

export async function archiveGroup(groupId: string) {
  return apiRequest<{ message?: string } | BackendGroup>(`/groups/${groupId}/archive/`, {
    method: 'POST',
  });
}

export async function restoreGroup(groupId: string) {
  return updateGroup(groupId, {
    status: 'ACTIVE',
  });
}

export async function leaveGroup(groupId: string) {
  return apiRequest<{ message?: string }>(`/groups/${groupId}/leave/`, {
    method: 'POST',
  });
}

export async function getGroupMembers(groupId: string) {
  const data = await apiRequest<
    BackendGroupMember[] | { results?: BackendGroupMember[]; data?: BackendGroupMember[] }
  >(`/groups/${groupId}/members/`);

  return unwrapList(data);
}

export async function removeGroupMember(groupId: string, memberId: string) {
  return apiRequest<{ message?: string }>(
    `/groups/${groupId}/members/${memberId}/remove/`,
    {
      method: 'POST',
    },
  );
}

export async function createGroupInvite(
  groupId: string,
  input: CreateInviteInput = {},
) {
  return apiRequest<CreatedInvite>(`/groups/${groupId}/invites/`, {
    method: 'POST',
    body: JSON.stringify({
      expires_in_hours: input.expires_in_hours ?? 72,
      max_uses: input.max_uses ?? 10,
    }),
  });
}

export async function revokeGroupInvite(groupId: string, inviteId: string) {
  return apiRequest<{ message?: string }>(
    `/groups/${groupId}/invites/${inviteId}/revoke/`,
    {
      method: 'POST',
    },
  );
}

export async function getInvitePreview(token: string) {
  return apiRequest<InvitePreview>(`/groups/invites/${encodeURIComponent(token)}/`, {
    auth: false,
  });
}

export async function acceptInvite(token: string) {
  return apiRequest<{ message?: string } | BackendGroup>(
    `/groups/invites/${encodeURIComponent(token)}/accept/`,
    {
      method: 'POST',
    },
  );
}
