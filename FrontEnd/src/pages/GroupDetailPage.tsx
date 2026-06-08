import { useEffect, useMemo, useState } from 'react';
import {
  Archive,
  ArrowLeft,
  Check,
  Copy,
  Crown,
  Link2,
  LockKeyhole,
  LogOut,
  RefreshCw,
  RotateCcw,
  Save,
  Trash2,
  UserMinus,
  Users,
} from 'lucide-react';
import { InlineLoader, useFeedback } from '../components/feedback/FeedbackProvider';
import { isApiError } from '../lib/api';
import {
  archiveGroup,
  createGroupInvite,
  getGroupDetail,
  getGroupMembers,
  getInviteId,
  getInviteUrl,
  leaveGroup,
  removeGroupMember,
  restoreGroup,
  revokeGroupInvite,
  updateGroup,
  type BackendGroup,
  type BackendGroupMember,
  type BackendGroupType,
  type CreatedInvite,
} from '../lib/groupApi';

interface GroupDetailPageProps {
  groupId: string;
  onBack: () => void;
  onGroupUpdated: (group: BackendGroup) => void;
  onGroupRemoved: (groupId: string) => void;
}

function getMemberId(member: BackendGroupMember) {
  return member.id || member.member_id || member.user_id || '';
}

function getMemberName(member: BackendGroupMember) {
  return member.display_name || member.full_name || member.phone_number || member.phone || 'عضو گروه';
}

function getMemberPhone(member: BackendGroupMember) {
  return member.phone_number || member.phone || 'شماره ثبت نشده';
}

function getRoleLabel(role?: string) {
  if (role === 'OWNER') return 'مالک';
  if (role === 'ADMIN') return 'مدیر';
  if (role === 'MEMBER') return 'عضو';
  return role || 'عضو';
}

function getGroupTypeLabel(type?: BackendGroupType) {
  if (type === 'EVENT') return 'رویداد';
  return 'عمومی';
}

function getBackendMessage(error: unknown) {
  if (isApiError(error)) {
    if (typeof error.body === 'object' && error.body && 'detail' in error.body) {
      return String((error.body as { detail?: unknown }).detail);
    }

    if (error.bodyText) return error.bodyText;
  }

  return '';
}

export function GroupDetailPage({
  groupId,
  onBack,
  onGroupUpdated,
  onGroupRemoved,
}: GroupDetailPageProps) {
  const { notify, confirm } = useFeedback();

  const [group, setGroup] = useState<BackendGroup | null>(null);
  const [members, setMembers] = useState<BackendGroupMember[]>([]);
  const [invite, setInvite] = useState<CreatedInvite | null>(null);

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [groupType, setGroupType] = useState<BackendGroupType>('GENERAL');

  const [loading, setLoading] = useState(true);
  const [membersLoading, setMembersLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [archiveLoading, setArchiveLoading] = useState(false);
  const [leaveLoading, setLeaveLoading] = useState(false);
  const [inviteLoading, setInviteLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const inviteUrl = useMemo(() => {
    return invite ? getInviteUrl(invite) : '';
  }, [invite]);

  const isArchived = group?.status === 'ARCHIVED';
  const isOwner = group?.my_role === 'OWNER';

  async function loadGroup() {
    try {
      setLoading(true);
      setError(null);

      const backendGroup = await getGroupDetail(groupId);

      setGroup(backendGroup);
      setTitle(backendGroup.title || '');
      setDescription(backendGroup.description || '');
      setGroupType(backendGroup.group_type || 'GENERAL');
      onGroupUpdated(backendGroup);
    } catch (err) {
      console.error(err);
      setError('خطا در دریافت جزئیات گروه');
    } finally {
      setLoading(false);
    }
  }

  async function loadMembers() {
    try {
      setMembersLoading(true);
      const backendMembers = await getGroupMembers(groupId);
      setMembers(backendMembers);
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'دریافت اعضا ناموفق بود',
        description: getBackendMessage(err) || 'Network و Console را بررسی کن.',
      });
    } finally {
      setMembersLoading(false);
    }
  }

  useEffect(() => {
    loadGroup();
    loadMembers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groupId]);

  async function handleSave() {
    try {
      setSaving(true);

      const updatedGroup = await updateGroup(groupId, {
        title: title.trim(),
        description: description.trim(),
        group_type: groupType,
      });

      setGroup(updatedGroup);
      onGroupUpdated(updatedGroup);
      notify({
        type: 'success',
        title: 'تغییرات ذخیره شد',
        description: 'اطلاعات گروه با موفقیت بروزرسانی شد.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'ویرایش گروه ناموفق بود',
        description: getBackendMessage(err) || 'Network و Console را بررسی کن.',
      });
    } finally {
      setSaving(false);
    }
  }

  async function handleArchive() {
    if (isArchived) {
      notify({
        type: 'info',
        title: 'این گروه قبلاً آرشیو شده',
        description: 'برای فعال‌کردن دوباره از دکمه بازگردانی استفاده کن.',
      });
      return;
    }

    const confirmed = await confirm({
      title: 'آرشیو گروه؟',
      description:
        'بعد از آرشیو، گروه از لیست گروه‌های فعال حذف می‌شود و فقط در بخش گروه‌های آرشیو شده نمایش داده می‌شود.',
      confirmText: 'آرشیو کن',
      cancelText: 'انصراف',
      tone: 'warning',
    });

    if (!confirmed) return;

    try {
      setArchiveLoading(true);
      await archiveGroup(groupId);
      const refreshedGroup = await getGroupDetail(groupId);

      setGroup(refreshedGroup);
      onGroupUpdated(refreshedGroup);
      notify({
        type: 'success',
        title: 'گروه آرشیو شد',
        description: 'این گروه از لیست گروه‌های فعال خارج شد.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'آرشیو گروه ناموفق بود',
        description: getBackendMessage(err) || 'Network و Console را بررسی کن.',
      });
    } finally {
      setArchiveLoading(false);
    }
  }

  async function handleRestore() {
    if (!isArchived) {
      notify({
        type: 'info',
        title: 'این گروه فعال است',
        description: 'نیازی به بازگردانی نیست.',
      });
      return;
    }

    const confirmed = await confirm({
      title: 'بازگردانی گروه؟',
      description:
        'اگر بک‌اند تغییر وضعیت گروه را پشتیبانی کند، این گروه دوباره در لیست گروه‌های فعال نمایش داده می‌شود.',
      confirmText: 'فعال کن',
      cancelText: 'انصراف',
      tone: 'success',
    });

    if (!confirmed) return;

    try {
      setArchiveLoading(true);
      const restoredGroup = await restoreGroup(groupId);

      setGroup(restoredGroup);
      onGroupUpdated(restoredGroup);
      notify({
        type: 'success',
        title: 'گروه دوباره فعال شد',
        description: 'این گروه حالا در لیست گروه‌های فعال نمایش داده می‌شود.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'بازگردانی گروه ناموفق بود',
        description:
          getBackendMessage(err) ||
          'احتمالاً بک‌اند هنوز endpoint یا فیلد status برای فعال‌سازی دوباره ندارد.',
      });
    } finally {
      setArchiveLoading(false);
    }
  }

  async function handleLeave() {
    if (isOwner) {
      notify({
        type: 'info',
        title: 'مالک گروه نمی‌تواند خارج شود',
        description:
          'این محدودیت از سمت بک‌اند است. برای مالک، فعلاً آرشیو گروه یا انتقال مالکیت لازم است.',
      });
      return;
    }

    const confirmed = await confirm({
      title: 'خروج از گروه؟',
      description: 'بعد از خروج، این گروه از لیست گروه‌های تو حذف می‌شود.',
      confirmText: 'خارج شو',
      cancelText: 'انصراف',
      tone: 'danger',
    });

    if (!confirmed) return;

    try {
      setLeaveLoading(true);
      await leaveGroup(groupId);
      notify({
        type: 'success',
        title: 'از گروه خارج شدی',
        description: 'گروه از لیست تو حذف شد.',
      });
      onGroupRemoved(groupId);
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'خروج از گروه ناموفق بود',
        description:
          getBackendMessage(err) ||
          'اگر مالک گروه هستی، بک‌اند اجازه خروج مالک را نمی‌دهد.',
      });
    } finally {
      setLeaveLoading(false);
    }
  }

  async function handleRemoveMember(member: BackendGroupMember) {
    const memberId = getMemberId(member);

    if (!memberId) {
      notify({
        type: 'error',
        title: 'شناسه عضو پیدا نشد',
        description: 'پاسخ بک‌اند برای عضو id یا member_id ندارد.',
      });
      return;
    }

    const confirmed = await confirm({
      title: 'حذف عضو؟',
      description: `${getMemberName(member)} از گروه حذف شود؟`,
      confirmText: 'حذف کن',
      cancelText: 'انصراف',
      tone: 'danger',
    });

    if (!confirmed) return;

    try {
      await removeGroupMember(groupId, memberId);
      setMembers((prev) => prev.filter((item) => getMemberId(item) !== memberId));
      notify({
        type: 'success',
        title: 'عضو حذف شد',
        description: 'لیست اعضا بروزرسانی شد.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'حذف عضو ناموفق بود',
        description: getBackendMessage(err) || 'Network و Console را بررسی کن.',
      });
    }
  }

  async function handleCreateInvite() {
    try {
      setInviteLoading(true);

      const createdInvite = await createGroupInvite(groupId, {
        expires_in_hours: 72,
        max_uses: 10,
      });

      setInvite(createdInvite);
      notify({
        type: 'success',
        title: 'لینک دعوت ساخته شد',
        description: 'لینک را کپی کن و برای کاربر دیگر بفرست.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'ساخت لینک دعوت ناموفق بود',
        description: getBackendMessage(err) || 'Network و Console را بررسی کن.',
      });
    } finally {
      setInviteLoading(false);
    }
  }

  async function handleCopyInvite() {
    if (!inviteUrl) {
      notify({
        type: 'error',
        title: 'لینک دعوت موجود نیست',
        description: 'پاسخ بک‌اند token یا invite_url نداشت.',
      });
      return;
    }

    try {
      await navigator.clipboard.writeText(inviteUrl);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
      notify({
        type: 'success',
        title: 'لینک کپی شد',
        description: 'حالا می‌تونی لینک را برای کاربر دیگر بفرستی.',
      });
    } catch {
      setCopied(false);
      notify({
        type: 'error',
        title: 'کپی لینک ناموفق بود',
        description: 'دسترسی clipboard مرورگر فعال نیست.',
      });
    }
  }

  async function handleRevokeInvite() {
    if (!invite) return;

    const inviteId = getInviteId(invite);

    if (!inviteId) {
      notify({
        type: 'error',
        title: 'شناسه دعوت در پاسخ بک‌اند نیست',
        description: 'برای لغو دعوت، بک‌اند باید id یا invite_id برگرداند.',
      });
      return;
    }

    const confirmed = await confirm({
      title: 'لغو لینک دعوت؟',
      description: 'بعد از لغو، این لینک دیگر برای عضویت قابل استفاده نیست.',
      confirmText: 'لغو کن',
      cancelText: 'انصراف',
      tone: 'danger',
    });

    if (!confirmed) return;

    try {
      await revokeGroupInvite(groupId, inviteId);
      setInvite(null);
      notify({
        type: 'success',
        title: 'لینک دعوت لغو شد',
        description: 'این دعوت دیگر قابل استفاده نیست.',
      });
    } catch (err) {
      console.error(err);
      notify({
        type: 'error',
        title: 'لغو دعوت ناموفق بود',
        description: getBackendMessage(err) || 'Network و Console را بررسی کن.',
      });
    }
  }

  return (
    <main className="px-4 py-6 sm:px-6 xl:px-8">
      <div className="mx-auto max-w-[1180px] space-y-6">
        <div className="flex flex-col gap-4 rounded-3xl border border-border bg-white p-6 shadow-soft lg:flex-row lg:items-center lg:justify-between">
          <div className="text-right">
            <button
              type="button"
              onClick={onBack}
              className="mb-4 inline-flex items-center gap-2 text-sm font-semibold text-slate-600 transition hover:text-text"
            >
              <ArrowLeft className="h-4.5 w-4.5" />
              بازگشت به گروه‌ها
            </button>

            <h1 className="text-[30px] font-extrabold tracking-[-0.03em] text-text">
              {loading ? 'در حال دریافت گروه...' : group?.title || 'جزئیات گروه'}
            </h1>

            <p className="mt-2 text-sm leading-7 text-muted">
              مدیریت اطلاعات گروه، اعضا و لینک‌های دعوت
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => {
                loadGroup();
                loadMembers();
              }}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl border border-border bg-white px-4 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
            >
              <RefreshCw className="h-4 w-4" />
              بروزرسانی
            </button>

            {isArchived ? (
              <button
                type="button"
                onClick={handleRestore}
                disabled={archiveLoading}
                className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl border border-emerald-100 bg-emerald-50 px-4 text-sm font-semibold text-emerald-700 transition hover:bg-emerald-100 disabled:opacity-60"
              >
                {archiveLoading ? <InlineLoader label="در حال فعال‌سازی..." /> : <><RotateCcw className="h-4 w-4" /> بازگردانی</>}
              </button>
            ) : (
              <button
                type="button"
                onClick={handleArchive}
                disabled={archiveLoading}
                className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl border border-amber-100 bg-amber-50 px-4 text-sm font-semibold text-amber-700 transition hover:bg-amber-100 disabled:opacity-60"
              >
                {archiveLoading ? <InlineLoader label="در حال آرشیو..." /> : <><Archive className="h-4 w-4" /> آرشیو</>}
              </button>
            )}

            <button
              type="button"
              onClick={handleLeave}
              disabled={leaveLoading || isOwner}
              title={isOwner ? 'مالک گروه نمی‌تواند از گروه خارج شود' : undefined}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl border border-rose-100 bg-rose-50 px-4 text-sm font-semibold text-rose-600 transition hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-55"
            >
              {isOwner ? <LockKeyhole className="h-4 w-4" /> : <LogOut className="h-4 w-4" />}
              {leaveLoading ? 'در حال خروج...' : 'خروج'}
            </button>
          </div>
        </div>

        {error ? (
          <div className="rounded-3xl border border-rose-100 bg-rose-50 p-5 text-center text-sm font-semibold text-rose-600">
            {error}
          </div>
        ) : null}

        {isOwner ? (
          <div className="rounded-3xl border border-sky-100 bg-sky-50 p-4 text-right text-sm leading-7 text-sky-700">
            تو مالک این گروه هستی؛ خروج مالک از گروه معمولاً توسط بک‌اند مجاز نیست. برای مخفی‌کردن گروه از لیست فعال‌ها از آرشیو استفاده کن.
          </div>
        ) : null}

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
          <section className="space-y-6">
            <div className="rounded-3xl border border-border bg-white p-6 shadow-soft">
              <div className="mb-6 flex items-center justify-between">
                <div className="text-right">
                  <h2 className="text-2xl font-bold text-text">تنظیمات گروه</h2>
                  <p className="mt-1 text-sm text-muted">
                    عنوان، توضیح و نوع گروه را ویرایش کن.
                  </p>
                </div>

                <div
                  className={[
                    'rounded-2xl px-3 py-2 text-sm font-bold',
                    isArchived
                      ? 'bg-amber-50 text-amber-700'
                      : 'bg-emerald-50 text-emerald-700',
                  ].join(' ')}
                >
                  {isArchived ? 'آرشیو شده' : 'فعال'}
                </div>
              </div>

              <div className="grid gap-5 md:grid-cols-2">
                <div>
                  <label className="mb-2 block text-sm font-semibold text-text">
                    عنوان گروه
                  </label>
                  <input
                    dir="rtl"
                    value={title}
                    onChange={(event) => setTitle(event.target.value)}
                    className="h-12 w-full rounded-2xl border border-border bg-white px-4 text-sm text-text outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
                  />
                </div>

                <div>
                  <label className="mb-2 block text-sm font-semibold text-text">
                    نوع گروه
                  </label>
                  <select
                    value={groupType}
                    onChange={(event) => setGroupType(event.target.value as BackendGroupType)}
                    className="h-12 w-full rounded-2xl border border-border bg-white px-4 text-sm text-text outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
                  >
                    <option value="GENERAL">عمومی</option>
                    <option value="EVENT">رویداد</option>
                  </select>
                </div>
              </div>

              <div className="mt-5">
                <label className="mb-2 block text-sm font-semibold text-text">
                  توضیحات
                </label>
                <textarea
                  dir="rtl"
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  className="min-h-[120px] w-full resize-none rounded-2xl border border-border bg-white px-4 py-3 text-sm leading-7 text-text outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10"
                />
              </div>

              <div className="mt-5 flex justify-end">
                <button
                  type="button"
                  onClick={handleSave}
                  disabled={saving}
                  className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl bg-gradient-to-l from-[#00915F] to-[#00A86B] px-6 text-sm font-semibold text-white shadow-[0_12px_28px_rgba(0,168,107,0.22)] transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {saving ? <InlineLoader label="در حال ذخیره..." /> : <><Save className="h-4.5 w-4.5" /> ذخیره تغییرات</>}
                </button>
              </div>
            </div>

            <div className="rounded-3xl border border-border bg-white p-6 shadow-soft">
              <div className="mb-6 flex items-center justify-between">
                <div className="text-right">
                  <h2 className="text-2xl font-bold text-text">اعضای گروه</h2>
                  <p className="mt-1 text-sm text-muted">
                    اعضای فعلی گروه را مشاهده و مدیریت کن.
                  </p>
                </div>

                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600">
                  <Users className="h-5 w-5" />
                </div>
              </div>

              {membersLoading ? (
                <div className="rounded-2xl border border-border bg-slate-50 p-5 text-center text-sm text-muted">
                  در حال دریافت اعضا...
                </div>
              ) : null}

              {!membersLoading && members.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-border p-8 text-center text-sm text-muted">
                  هنوز عضوی برای نمایش وجود ندارد.
                </div>
              ) : null}

              <div className="space-y-3">
                {members.map((member) => {
                  const memberId = getMemberId(member);
                  const memberRole = member.role;
                  const cannotRemove = memberRole === 'OWNER';

                  return (
                    <div
                      key={memberId || getMemberName(member)}
                      className="flex flex-col gap-4 rounded-2xl border border-border bg-white px-4 py-4 sm:flex-row sm:items-center sm:justify-between"
                    >
                      <div className="flex min-w-0 items-center gap-3">
                        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-300 to-teal-600 text-sm font-bold text-white">
                          {getMemberName(member).slice(0, 1)}
                        </div>

                        <div className="min-w-0 text-right">
                          <div className="truncate text-base font-bold text-text">
                            {getMemberName(member)}
                          </div>
                          <div className="mt-1 text-sm text-muted">
                            {getMemberPhone(member)}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center justify-between gap-3 sm:justify-end">
                        <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-700">
                          <Crown className="h-3.5 w-3.5" />
                          {getRoleLabel(memberRole)}
                        </span>

                        <button
                          type="button"
                          onClick={() => handleRemoveMember(member)}
                          disabled={cannotRemove || !memberId}
                          className="inline-flex h-9 items-center justify-center gap-1.5 rounded-xl bg-rose-50 px-3 text-xs font-semibold text-rose-600 transition hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-45"
                        >
                          <UserMinus className="h-3.5 w-3.5" />
                          حذف
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </section>

          <aside className="space-y-6">
            <div className="rounded-3xl border border-emerald-100 bg-emerald-50/50 p-6 shadow-soft">
              <div className="mb-5 flex items-center justify-between">
                <div className="text-right">
                  <h2 className="text-xl font-bold text-text">خلاصه گروه</h2>
                  <p className="mt-1 text-sm text-muted">اطلاعات سریع گروه</p>
                </div>

                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white text-emerald-600">
                  <Check className="h-5 w-5" />
                </div>
              </div>

              <div className="space-y-4 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-muted">نوع گروه</span>
                  <span className="font-bold text-text">{getGroupTypeLabel(group?.group_type)}</span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-muted">وضعیت</span>
                  <span className="font-bold text-text">
                    {isArchived ? 'آرشیو شده' : 'فعال'}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-muted">نقش شما</span>
                  <span className="font-bold text-text">{getRoleLabel(group?.my_role)}</span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-muted">تعداد اعضا</span>
                  <span className="font-bold text-text">
                    {(group?.member_count ?? members.length).toLocaleString('fa-IR')} نفر
                  </span>
                </div>
              </div>
            </div>

            <div className="rounded-3xl border border-border bg-white p-6 shadow-soft">
              <div className="mb-5 text-right">
                <h2 className="text-xl font-bold text-text">دعوت اعضا</h2>
                <p className="mt-1 text-sm leading-7 text-muted">
                  لینک دعوت بساز، کپی کن و برای کاربر دیگر بفرست. کاربر با بازکردن یا پیست‌کردن لینک می‌تواند عضو گروه شود.
                </p>
              </div>

              {!invite ? (
                <button
                  type="button"
                  onClick={handleCreateInvite}
                  disabled={inviteLoading || isArchived}
                  className="inline-flex h-12 w-full items-center justify-center gap-2 rounded-2xl bg-gradient-to-l from-[#00915F] to-[#00A86B] px-5 text-sm font-semibold text-white shadow-[0_12px_28px_rgba(0,168,107,0.18)] transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <Link2 className="h-4.5 w-4.5" />
                  {inviteLoading ? 'در حال ساخت...' : 'ساخت لینک دعوت'}
                </button>
              ) : (
                <div className="space-y-3">
                  <div className="relative">
                    <Link2 className="pointer-events-none absolute right-4 top-1/2 h-4.5 w-4.5 -translate-y-1/2 text-slate-400" />
                    <input
                      readOnly
                      dir="ltr"
                      value={inviteUrl || 'لینک در پاسخ بک‌اند وجود ندارد'}
                      className="h-12 w-full rounded-2xl border border-border bg-slate-50 pr-11 pl-4 text-left text-sm text-slate-700 outline-none"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <button
                      type="button"
                      onClick={handleCopyInvite}
                      disabled={!inviteUrl}
                      className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl border border-emerald-100 bg-emerald-50 px-4 text-sm font-semibold text-emerald-700 transition hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      <Copy className="h-4 w-4" />
                      {copied ? 'کپی شد' : 'کپی'}
                    </button>

                    <button
                      type="button"
                      onClick={handleRevokeInvite}
                      className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl border border-rose-100 bg-rose-50 px-4 text-sm font-semibold text-rose-600 transition hover:bg-rose-100"
                    >
                      <Trash2 className="h-4 w-4" />
                      لغو
                    </button>
                  </div>

                  {invite.expires_at ? (
                    <p className="text-center text-xs text-muted">
                      اعتبار تا: {invite.expires_at}
                    </p>
                  ) : null}
                </div>
              )}
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}
