import { apiRequest, isApiError } from './api';

export type BackendGroupType = 'GENERAL' | 'EVENT';
export type BackendGroupStatus = 'ACTIVE' | 'ARCHIVED';

interface BackendMemberIdentity {
  id?: string;
  user_id?: string;
  art_name?: string;
  username?: string;
  display_name?: string;
  full_name?: string;
  first_name?: string;
  last_name?: string;
  name?: string;
  phone_number?: string;
  phone?: string;
  mobile?: string;
  email?: string;
  profile?: BackendMemberIdentity | null;
  user?: BackendMemberIdentity | null;
  member?: BackendMemberIdentity | null;
  invited_user?: BackendMemberIdentity | null;
  participant?: BackendMemberIdentity | null;
  [key: string]: unknown;
}

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
  first_name?: string;
  last_name?: string;
  name?: string;
  phone_number?: string;
  phone?: string;
  mobile?: string;
  email?: string;
  role?: string;
  joined_at?: string;

  user?: BackendMemberIdentity | null;
  profile?: BackendMemberIdentity | null;
  member?: BackendMemberIdentity | null;
  invited_user?: BackendMemberIdentity | null;
  participant?: BackendMemberIdentity | null;
  [key: string]: unknown;
}

export interface CreateGroupInput {
  title: string;
  description?: string;
  group_type?: BackendGroupType;
  member_user_ids?: string[];
  member_emails?: string[];
  member_phones?: string[];
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

function asRecord(value: unknown) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return null;
  }

  return value as Record<string, unknown>;
}

function readString(value: unknown) {
  return typeof value === 'string' ? value.trim() : '';
}

function joinNameParts(
  firstName: string | undefined,
  lastName: string | undefined,
) {
  return [firstName, lastName].filter(Boolean).join(' ').trim();
}

function normalizeStringList(values: Array<string | undefined>) {
  return values.filter(Boolean).map((value) => value!.trim()).filter(Boolean);
}

function uniqueStrings(values: Array<string | undefined>) {
  return Array.from(new Set(normalizeStringList(values)));
}

function isEmailLike(value?: string) {
  return Boolean(value && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value));
}

function getMemberRecords(member: BackendGroupMember) {
  const records: Record<string, unknown>[] = [];
  const queue: Array<Record<string, unknown> | null> = [
    asRecord(member),
    asRecord(member.user),
    asRecord(member.profile),
    asRecord(member.member),
    asRecord(member.invited_user),
    asRecord(member.participant),
  ];
  const seen = new Set<Record<string, unknown>>();

  while (queue.length > 0) {
    const current = queue.shift();

    if (!current || seen.has(current)) {
      continue;
    }

    seen.add(current);
    records.push(current);

    const nestedRecords = [
      asRecord(current.profile),
      asRecord(current.user),
      asRecord(current.member),
      asRecord(current.invited_user),
      asRecord(current.participant),
    ];

    nestedRecords.forEach((nestedRecord) => {
      if (nestedRecord && !seen.has(nestedRecord)) {
        queue.push(nestedRecord);
      }
    });
  }

  return records;
}

function getRecordNameCandidates(record: Record<string, unknown>) {
  const joinedName = joinNameParts(
    readString(record.first_name),
    readString(record.last_name),
  );

  return {
    preferred: uniqueStrings([
      readString(record.art_name),
      readString(record.username),
      readString(record.display_name),
      readString(record.full_name),
      readString(record.name),
      joinedName,
    ]).filter((value) => !isEmailLike(value)),
    fallback: uniqueStrings([
      readString(record.display_name_snapshot),
      readString(record.email),
    ]),
  };
}

function getRecordPhone(record: Record<string, unknown>) {
  return [
    readString(record.phone_number),
    readString(record.phone),
    readString(record.mobile),
  ].find(Boolean) || '';
}

function getRecordEmail(record: Record<string, unknown>) {
  return readString(record.email);
}

export function getBackendGroupMemberId(member: BackendGroupMember) {
  const records = getMemberRecords(member);

  return [
    readString(member.member_id),
    readString(member.id),
    ...records.map((record) => readString(record.member_id)),
    ...records.map((record) => readString(record.id)),
  ].find(Boolean) || '';
}

export function getBackendGroupMemberUserId(member: BackendGroupMember) {
  const records = getMemberRecords(member);

  return [
    readString(member.user_id),
    ...records.map((record) => readString(record.user_id)),
    readString(member.id),
    ...records.map((record) => readString(record.id)),
  ].find(Boolean) || '';
}

export function getBackendGroupMemberName(member: BackendGroupMember) {
  const records = getMemberRecords(member);
  const preferredNames = uniqueStrings(
    records.flatMap((record) => getRecordNameCandidates(record).preferred),
  );
  const visibleName = preferredNames[0];

  if (visibleName) {
    return visibleName;
  }

  const safeFallbackName = uniqueStrings(
    records.flatMap((record) => getRecordNameCandidates(record).fallback),
  ).find((value) => !isEmailLike(value));

  if (safeFallbackName) {
    return safeFallbackName;
  }

  return (
    records.map(getRecordPhone).find(Boolean) ||
    records.map(getRecordEmail).find(Boolean) ||
    'عضو گروه'
  );
}

export function getBackendGroupMemberPhone(member: BackendGroupMember) {
  return getMemberRecords(member).map(getRecordPhone).find(Boolean) || 'شماره ثبت نشده';
}

export function getBackendGroupMemberEmail(member: BackendGroupMember) {
  return getMemberRecords(member).map(getRecordEmail).find(Boolean) || '';
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

async function requestGroupList(path: string) {
  const data = await apiRequest<
    BackendGroup[] | { results?: BackendGroup[]; data?: BackendGroup[] }
  >(path);

  return unwrapList(data);
}

function shouldRetryAlternateGroupEndpoint(error: unknown) {
  return isApiError(error) && [400, 404, 405, 500, 502, 503, 504].includes(error.status);
}

export async function getMyGroups() {
  try {
    return await requestGroupList('/groups/mine/');
  } catch (error) {
    if (!shouldRetryAlternateGroupEndpoint(error)) {
      throw error;
    }

    console.warn('Could not load /groups/mine/. Retrying /groups/.', error);
    return requestGroupList('/groups/');
  }
}

function buildCreateGroupBasePayload(input: CreateGroupInput) {
  return {
    title: input.title.trim(),
    description: input.description?.trim() || '',
    group_type: input.group_type || 'GENERAL',
  };
}

function buildCreateGroupMemberPayload(input: CreateGroupInput) {
  const memberUserIds = uniqueStrings(input.member_user_ids);
  const memberPhones = uniqueStrings(input.member_phones);
  const memberEmails = uniqueStrings(input.member_emails);

  if (!memberUserIds.length && !memberPhones.length && !memberEmails.length) {
    return null;
  }

  const members = [
    ...memberUserIds.map((userId) => ({ user_id: userId })),
    ...memberPhones.map((phoneNumber) => ({ phone_number: phoneNumber })),
    ...memberEmails.map((email) => ({ email })),
  ];

  return {
    member_user_ids: memberUserIds,
    member_ids: memberUserIds,
    user_ids: memberUserIds,
    members,
  };
}

function shouldRetryCreateGroupWithoutMembers(error: unknown) {
  if (!isApiError(error) || ![400, 422].includes(error.status)) {
    return false;
  }

  const normalizedBody = JSON.stringify(error.body || '').toLowerCase();
  return (
    normalizedBody.includes('member') ||
    normalizedBody.includes('members') ||
    normalizedBody.includes('user_ids') ||
    normalizedBody.includes('extra fields not permitted') ||
    normalizedBody.includes('unknown field')
  );
}

async function requestCreateGroup(path: string, payload: Record<string, unknown>) {
  return apiRequest<BackendGroup>(path, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function createGroup(input: CreateGroupInput) {
  const basePayload = buildCreateGroupBasePayload(input);
  const memberPayload = buildCreateGroupMemberPayload(input);
  const preferredPath = '/groups/mine/';
  const fallbackPath = '/groups/';

  async function createOnAvailableEndpoint(payload: Record<string, unknown>) {
    try {
      return await requestCreateGroup(preferredPath, payload);
    } catch (error) {
      if (!shouldRetryAlternateGroupEndpoint(error)) {
        throw error;
      }

      console.warn('Could not create group via /groups/mine/. Retrying /groups/.', error);
      return requestCreateGroup(fallbackPath, payload);
    }
  }

  if (!memberPayload) {
    return createOnAvailableEndpoint(basePayload);
  }

  try {
    return await createOnAvailableEndpoint({
      ...basePayload,
      ...memberPayload,
    });
  } catch (error) {
    if (!shouldRetryCreateGroupWithoutMembers(error)) {
      throw error;
    }

    return createOnAvailableEndpoint(basePayload);
  }
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
  try {
    return await apiRequest<BackendGroup>(`/groups/${groupId}/restore/`, {
      method: 'POST',
    });
  } catch (error) {
    if (!shouldRetryAlternateGroupEndpoint(error)) {
      throw error;
    }

    console.warn('Could not restore group via restore endpoint. Retrying PATCH status.', error);
    return updateGroup(groupId, {
      status: 'ACTIVE',
    });
  }
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
