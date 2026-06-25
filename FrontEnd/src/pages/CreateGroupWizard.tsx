import { useEffect, useMemo, useState } from 'react';
import {
  ArrowLeft,
  Check,
  ChevronLeft,
  CircleHelp,
  Home,
  Loader2,
  Plane,
  Search,
  Trash2,
  Users,
  UtensilsCrossed,
  X,
} from 'lucide-react';
import {
  getBackendGroupMemberEmail,
  getBackendGroupMemberName,
  getBackendGroupMemberPhone,
  getBackendGroupMemberUserId,
  getGroupMembers,
  getMyGroups,
  type BackendGroupMember,
} from '../lib/groupApi';
import { getCurrentUser, type CurrentUser } from '../lib/userApi';

export type GroupTypeValue = '' | 'travel' | 'food' | 'home' | 'other';

export interface CreatedGroupPayload {
  name: string;
  description: string;
  groupType: GroupTypeValue;
  memberCount: number;
  selectedUserIds?: string[];
  selectedPhones?: string[];
  selectedEmails?: string[];
}

interface CreateGroupWizardProps {
  onBack: () => void;
  onComplete: (payload: CreatedGroupPayload) => void;
}

interface Contact {
  id: string;
  name: string;
  phone: string;
  email?: string;
  userId?: string;
  avatar: string;
  avatarClass: string;
  sharedGroupCount: number;
  sourceLabel?: string;
}

interface GroupInfoErrors {
  name?: string;
  groupType?: string;
  form?: string;
}

interface GroupValues {
  name: string;
  description: string;
  groupType: GroupTypeValue;
}

type WizardStep = 1 | 2;

const groupTypeOptions: Array<{
  value: Exclude<GroupTypeValue, ''>;
  label: string;
  description: string;
  icon: typeof Plane;
}> = [
  {
    value: 'travel',
    label: 'سفر',
    description: 'خرج‌های سفر، ویلا، بنزین و غذا',
    icon: Plane,
  },
  {
    value: 'food',
    label: 'غذا',
    description: 'رستوران، کافه و دورهمی',
    icon: UtensilsCrossed,
  },
  {
    value: 'home',
    label: 'خانه',
    description: 'هم‌خانه، خرید خانه و قبض‌ها',
    icon: Home,
  },
  {
    value: 'other',
    label: 'سایر',
    description: 'برای هر گروه دلخواه',
    icon: Users,
  },
];

const avatarGradients = [
  'from-amber-300 via-orange-400 to-orange-600',
  'from-pink-300 to-rose-500',
  'from-cyan-300 to-sky-500',
  'from-emerald-300 to-teal-500',
  'from-violet-300 to-fuchsia-500',
  'from-indigo-300 to-blue-500',
  'from-lime-300 to-green-500',
];

function cn(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(' ');
}

function toPersianNumber(value: string | number) {
  return String(value).replace(/\d/g, (digit) => '۰۱۲۳۴۵۶۷۸۹'[Number(digit)]);
}

function normalizePhone(phone?: string | null) {
  return (phone || '').replace(/\s+/g, '').trim();
}

function normalizeText(value?: string | null) {
  return (value || '').trim().replace(/\s+/g, ' ').toLowerCase();
}

function getMemberName(member: BackendGroupMember) {
  return getBackendGroupMemberName(member);
}

function getMemberPhone(member: BackendGroupMember) {
  const phone = getBackendGroupMemberPhone(member);
  return phone === 'شماره ثبت نشده' ? '' : phone;
}

function getMemberEmail(member: BackendGroupMember) {
  return getBackendGroupMemberEmail(member);
}

function getMemberUserId(member: BackendGroupMember) {
  return getBackendGroupMemberUserId(member);
}

function isFallbackMemberName(name: string) {
  return !name || name === 'عضو گروه';
}

function shouldReplaceMemberCandidate(
  currentMember: BackendGroupMember,
  nextMember: BackendGroupMember,
) {
  const currentName = getMemberName(currentMember);
  const nextName = getMemberName(nextMember);

  if (isFallbackMemberName(currentName) && !isFallbackMemberName(nextName)) {
    return true;
  }

  if (!getMemberPhone(currentMember) && getMemberPhone(nextMember)) {
    return true;
  }

  return false;
}

function getMemberLookupKey(member: BackendGroupMember) {
  return (
    normalizeText(getMemberUserId(member)) ||
    normalizePhone(getMemberPhone(member)) ||
    normalizeText(getMemberEmail(member)) ||
    normalizeText(getMemberName(member))
  );
}

function isCurrentUserMember(member: BackendGroupMember, currentUser: CurrentUser | null) {
  if (!currentUser) return false;

  const memberUserId = normalizeText(getMemberUserId(member));
  const currentUserId = normalizeText(currentUser.id);

  if (memberUserId && currentUserId && memberUserId === currentUserId) {
    return true;
  }

  const memberPhone = normalizePhone(getMemberPhone(member));
  const currentPhone = normalizePhone(currentUser.phone_number || currentUser.phone);

  if (memberPhone && currentPhone && memberPhone === currentPhone) {
    return true;
  }

  const memberEmail = normalizeText(getMemberEmail(member));
  const currentEmail = normalizeText(currentUser.email);

  return Boolean(memberEmail && currentEmail && memberEmail === currentEmail);
}

function makeContactFromMember(
  member: BackendGroupMember,
  index: number,
  sharedGroupCount: number,
  groupTitles: string[],
): Contact {
  const name = getMemberName(member);
  const phone = getMemberPhone(member);
  const visibleGroupTitles = groupTitles.filter(Boolean).slice(0, 2);
  const extraGroupCount = Math.max(sharedGroupCount - visibleGroupTitles.length, 0);

  const sourceLabel =
    sharedGroupCount > 0
      ? `عضو مشترک در ${toPersianNumber(sharedGroupCount)} گروه${
          visibleGroupTitles.length ? `: ${visibleGroupTitles.join('، ')}` : ''
        }${extraGroupCount ? ` و ${toPersianNumber(extraGroupCount)} گروه دیگر` : ''}`
      : 'عضو گروه‌های قبلی';

  return {
    id: getMemberLookupKey(member) || String(index),
    name,
    phone: phone || 'شماره ثبت نشده',
    email: getMemberEmail(member) || undefined,
    userId: getMemberUserId(member) || undefined,
    avatar: name.slice(0, 1) || '؟',
    avatarClass: avatarGradients[index % avatarGradients.length],
    sharedGroupCount,
    sourceLabel,
  };
}

function validateGroupInfo(values: GroupValues): GroupInfoErrors {
  const errors: GroupInfoErrors = {};

  if (!values.name.trim()) {
    errors.name = 'نام گروه را وارد کن.';
  }

  if (!values.groupType) {
    errors.groupType = 'نوع گروه را انتخاب کن.';
  }

  if (errors.name || errors.groupType) {
    errors.form = 'برای ادامه فقط اسم گروه و نوع گروه لازم است.';
  }

  return errors;
}

function Avatar({ label, className }: { label: string; className: string }) {
  return (
    <div
      className={cn(
        'flex h-11 w-11 shrink-0 items-center justify-center rounded-[18px] bg-gradient-to-br text-sm font-extrabold text-white shadow-sm',
        className,
      )}
    >
      {label}
    </div>
  );
}

function CompactStepper({ currentStep }: { currentStep: WizardStep }) {
  return (
    <div className="rounded-[24px] border-2 border-slate-200 bg-white p-3 shadow-[0_14px_34px_rgba(15,23,42,0.06)]">
      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2" dir="rtl">
        <div
          className={cn(
            'rounded-[18px] px-4 py-3 text-center text-sm font-extrabold transition',
            currentStep === 1
              ? 'bg-emerald-600 text-white shadow-[0_12px_26px_rgba(16,185,129,0.18)]'
              : 'bg-emerald-50 text-emerald-700',
          )}
        >
          ۱. اطلاعات گروه
        </div>

        <ChevronLeft className="h-5 w-5 text-slate-300" />

        <div
          className={cn(
            'rounded-[18px] px-4 py-3 text-center text-sm font-extrabold transition',
            currentStep === 2
              ? 'bg-emerald-600 text-white shadow-[0_12px_26px_rgba(16,185,129,0.18)]'
              : 'bg-slate-50 text-slate-500',
          )}
        >
          ۲. اعضا
        </div>
      </div>
    </div>
  );
}

function FormError({ message }: { message?: string }) {
  if (!message) return null;

  return (
    <div className="rounded-[20px] border border-rose-100 bg-rose-50 px-4 py-3 text-right text-sm font-bold leading-7 text-rose-600">
      {message}
    </div>
  );
}

function GroupInfoStep({
  values,
  errors,
  onChange,
}: {
  values: GroupValues;
  errors: GroupInfoErrors;
  onChange: <K extends keyof GroupValues>(field: K, value: GroupValues[K]) => void;
}) {
  return (
    <section className="space-y-5">
      <div className="text-right">
        <h2 className="text-[25px] font-extrabold tracking-[-0.03em] text-text">
          اول گروهت رو بساز
        </h2>
        <p className="mt-2 text-sm font-semibold leading-7 text-muted">
          فقط اسم و نوع گروه لازمه. توضیحات اختیاریه.
        </p>
      </div>

      <FormError message={errors.form} />

      <div className="rounded-[28px] border-2 border-slate-200 bg-white p-4 shadow-[0_16px_38px_rgba(15,23,42,0.06)] sm:p-5">
        <label className="block text-right">
          <span className="mb-2 block text-sm font-extrabold text-text">نام گروه</span>
          <input
            dir="rtl"
            value={values.name}
            onChange={(event) => onChange('name', event.target.value)}
            placeholder="مثلاً سفر شمال، خانه، شام جمعه..."
            aria-invalid={Boolean(errors.name)}
            className={cn(
              'h-12 w-full rounded-[18px] border bg-slate-50/70 px-4 text-sm font-bold text-text outline-none transition placeholder:font-semibold placeholder:text-slate-400 focus:bg-white focus:ring-4',
              errors.name
                ? 'border-rose-200 focus:border-rose-300 focus:ring-rose-500/10'
                : 'border-slate-200 focus:border-emerald-300 focus:ring-emerald-500/10',
            )}
          />
          {errors.name ? (
            <span className="mt-2 block text-xs font-bold text-rose-500">{errors.name}</span>
          ) : null}
        </label>
      </div>

      <div className="rounded-[28px] border-2 border-slate-200 bg-white p-4 shadow-[0_16px_38px_rgba(15,23,42,0.06)] sm:p-5">
        <div className="mb-3 flex items-center justify-between gap-3 text-right">
          <div>
            <h3 className="text-base font-extrabold text-text">نوع گروه</h3>
            <p className="mt-1 text-xs font-semibold text-muted">
              فقط برای دسته‌بندی و ظاهر کارت استفاده می‌شه.
            </p>
          </div>

          {errors.groupType ? (
            <span className="rounded-full bg-rose-50 px-3 py-1 text-xs font-extrabold text-rose-500">
              انتخاب کن
            </span>
          ) : null}
        </div>

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {groupTypeOptions.map((option) => {
            const Icon = option.icon;
            const selected = values.groupType === option.value;

            return (
              <button
                key={option.value}
                type="button"
                onClick={() => onChange('groupType', option.value)}
                className={cn(
                  'min-h-[108px] rounded-[22px] border-2 p-4 text-right transition hover:-translate-y-0.5',
                  selected
                    ? 'border-emerald-300 bg-emerald-50 text-emerald-700 shadow-[0_14px_30px_rgba(16,185,129,0.14)]'
                    : 'border-slate-200 bg-white text-slate-700 hover:border-emerald-200 hover:bg-emerald-50/40',
                )}
              >
                <div className="mb-3 flex items-center justify-between gap-3">
                  <span
                    className={cn(
                      'flex h-10 w-10 items-center justify-center rounded-[16px]',
                      selected ? 'bg-emerald-600 text-white' : 'bg-slate-50 text-emerald-600',
                    )}
                  >
                    <Icon className="h-5 w-5" />
                  </span>

                  <span
                    className={cn(
                      'flex h-6 w-6 items-center justify-center rounded-full border',
                      selected
                        ? 'border-emerald-600 bg-emerald-600 text-white'
                        : 'border-slate-200 bg-white text-transparent',
                    )}
                  >
                    <Check className="h-4 w-4" />
                  </span>
                </div>

                <div className="text-base font-extrabold">{option.label}</div>
                <div className="mt-1 text-xs font-semibold leading-6 opacity-75">
                  {option.description}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      <div className="rounded-[28px] border-2 border-slate-200 bg-white p-4 shadow-[0_16px_38px_rgba(15,23,42,0.06)] sm:p-5">
        <label className="block text-right">
          <div className="mb-2 flex items-center justify-between gap-3">
            <span className="text-sm font-extrabold text-text">توضیحات اختیاری</span>
            <span className="text-xs font-bold text-slate-400">
              {toPersianNumber(values.description.length)}/۳۰۰
            </span>
          </div>

          <textarea
            dir="rtl"
            value={values.description}
            onChange={(event) => onChange('description', event.target.value.slice(0, 300))}
            placeholder="مثلاً هزینه‌های سفر ۴ روزه شمال"
            className="min-h-[96px] w-full resize-none rounded-[18px] border border-slate-200 bg-slate-50/70 px-4 py-3 text-sm font-semibold leading-7 text-text outline-none transition placeholder:text-slate-400 focus:border-emerald-300 focus:bg-white focus:ring-4 focus:ring-emerald-500/10"
          />
        </label>
      </div>
    </section>
  );
}

function ContactCard({
  contact,
  selected,
  onToggle,
}: {
  contact: Contact;
  selected: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className={cn(
        'flex items-center justify-between gap-3 rounded-[22px] border-2 px-4 py-3 text-right transition hover:-translate-y-0.5',
        selected
          ? 'border-emerald-300 bg-emerald-50 shadow-[0_12px_26px_rgba(16,185,129,0.12)]'
          : 'border-slate-200 bg-white hover:border-emerald-200 hover:bg-emerald-50/30',
      )}
    >
      <div className="flex min-w-0 items-center gap-3">
        <Avatar label={contact.avatar} className={contact.avatarClass} />

        <div className="min-w-0 text-right">
          <div className="truncate text-sm font-extrabold text-text">{contact.name}</div>
          <div className="mt-1 truncate text-xs font-semibold text-muted">{contact.phone}</div>
          {contact.sourceLabel ? (
            <div className="mt-1 truncate text-[11px] font-bold text-emerald-600">
              {contact.sourceLabel}
            </div>
          ) : null}
        </div>
      </div>

      <span
        className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-full border',
          selected
            ? 'border-emerald-600 bg-emerald-600 text-white'
            : 'border-slate-200 bg-slate-50 text-slate-300',
        )}
      >
        {selected ? <Check className="h-4 w-4" /> : <Users className="h-4 w-4" />}
      </span>
    </button>
  );
}

function MembersStep({
  contacts,
  contactsLoading,
  selectedIds,
  searchValue,
  onSearchChange,
  onToggleMember,
}: {
  contacts: Contact[];
  contactsLoading: boolean;
  selectedIds: string[];
  searchValue: string;
  onSearchChange: (value: string) => void;
  onToggleMember: (id: string) => void;
}) {
  const selectedContacts = contacts.filter((item) => selectedIds.includes(item.id));
  const normalizedSearch = normalizeText(searchValue);

  const visibleContacts = contacts.filter((contact) => {
    if (!normalizedSearch) return true;

    return (
      normalizeText(contact.name).includes(normalizedSearch) ||
      normalizePhone(contact.phone).includes(normalizedSearch) ||
      normalizeText(contact.email).includes(normalizedSearch)
    );
  });

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 text-right sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-[25px] font-extrabold tracking-[-0.03em] text-text">
            اعضا رو انتخاب کن
          </h2>
          <p className="mt-2 text-sm font-semibold leading-7 text-muted">
            این مرحله اختیاریه. بعداً هم از داخل گروه می‌تونی عضو دعوت کنی.
          </p>
        </div>

        <div className="rounded-[18px] border border-emerald-100 bg-emerald-50 px-4 py-3 text-right text-sm font-extrabold text-emerald-700">
          {toPersianNumber(selectedContacts.length)} نفر انتخاب شده
        </div>
      </div>

      <div className="rounded-[28px] border-2 border-slate-200 bg-white p-3 shadow-[0_16px_38px_rgba(15,23,42,0.06)]">
        <div className="relative">
          <Search className="pointer-events-none absolute right-4 top-1/2 h-4 w-4 -translate-y-1/2 text-emerald-600" />

          <input
            dir="rtl"
            value={searchValue}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="جستجو در اعضای قبلی..."
            className="h-12 w-full rounded-[18px] border border-slate-200 bg-slate-50/70 pr-11 pl-11 text-sm font-bold text-text outline-none transition placeholder:font-semibold placeholder:text-slate-400 focus:border-emerald-300 focus:bg-white focus:ring-4 focus:ring-emerald-500/10"
          />

          {searchValue ? (
            <button
              type="button"
              onClick={() => onSearchChange('')}
              className="absolute left-3 top-1/2 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded-full border border-slate-100 bg-white text-slate-500 shadow-sm transition hover:bg-rose-50 hover:text-rose-500"
              aria-label="پاک کردن جستجو"
            >
              <X className="h-4 w-4" />
            </button>
          ) : null}
        </div>
      </div>

      {selectedContacts.length > 0 ? (
        <div className="rounded-[28px] border-2 border-emerald-100 bg-white p-4 shadow-[0_16px_38px_rgba(15,23,42,0.06)]">
          <div className="mb-3 flex items-center justify-between gap-3 text-right">
            <div>
              <h3 className="text-base font-extrabold text-text">اعضای انتخاب‌شده</h3>
              <p className="mt-1 text-xs font-semibold text-muted">
                اگر اشتباهی انتخاب کردی، حذفش کن.
              </p>
            </div>
            <span className="flex h-9 min-w-9 items-center justify-center rounded-[15px] bg-emerald-50 px-3 text-sm font-extrabold text-emerald-700">
              {toPersianNumber(selectedContacts.length)}
            </span>
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            {selectedContacts.map((contact) => (
              <div
                key={contact.id}
                className="flex items-center justify-between gap-3 rounded-[20px] border border-slate-200 bg-slate-50/70 px-3 py-3"
              >
                <div className="flex min-w-0 items-center gap-3">
                  <Avatar label={contact.avatar} className={contact.avatarClass} />
                  <div className="min-w-0 text-right">
                    <div className="truncate text-sm font-extrabold text-text">{contact.name}</div>
                    <div className="mt-1 truncate text-xs font-semibold text-muted">
                      {contact.phone}
                    </div>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => onToggleMember(contact.id)}
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[15px] bg-white text-rose-500 shadow-sm transition hover:bg-rose-50"
                  aria-label="حذف عضو"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className="rounded-[28px] border-2 border-slate-200 bg-white p-4 shadow-[0_16px_38px_rgba(15,23,42,0.06)] sm:p-5">
        {contactsLoading ? (
          <div className="flex items-center justify-center gap-2 rounded-[22px] border border-slate-100 bg-slate-50 p-8 text-center text-sm font-bold text-muted">
            <Loader2 className="h-4 w-4 animate-spin" />
            در حال دریافت اعضای قبلی...
          </div>
        ) : null}

        {!contactsLoading && contacts.length === 0 ? (
          <div className="rounded-[22px] border-2 border-dashed border-slate-200 bg-slate-50/70 p-8 text-center">
            <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-[22px] bg-white text-emerald-600 shadow-sm">
              <CircleHelp className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-extrabold text-text">فعلاً عضو پیشنهادی نداریم</h3>
            <p className="mx-auto mt-2 max-w-[420px] text-sm font-semibold leading-7 text-muted">
              مشکلی نیست. گروه رو بساز؛ بعداً از داخل گروه لینک دعوت می‌سازی.
            </p>
          </div>
        ) : null}

        {!contactsLoading && contacts.length > 0 && visibleContacts.length === 0 ? (
          <div className="rounded-[22px] border-2 border-dashed border-slate-200 bg-slate-50/70 p-8 text-center text-sm font-semibold text-muted">
            نتیجه‌ای پیدا نشد. جستجو رو ساده‌تر کن.
          </div>
        ) : null}

        <div className="grid gap-3 md:grid-cols-2">
          {visibleContacts.map((contact) => (
            <ContactCard
              key={contact.id}
              contact={contact}
              selected={selectedIds.includes(contact.id)}
              onToggle={() => onToggleMember(contact.id)}
            />
          ))}
        </div>
      </div>
    </section>
  );
}

export function CreateGroupWizard({ onBack, onComplete }: CreateGroupWizardProps) {
  const [currentStep, setCurrentStep] = useState<WizardStep>(1);
  const [values, setValues] = useState<GroupValues>({
    name: '',
    groupType: '',
    description: '',
  });
  const [errors, setErrors] = useState<GroupInfoErrors>({});
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [contactsLoading, setContactsLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [searchValue, setSearchValue] = useState('');

  useEffect(() => {
    let ignore = false;

    async function loadContacts() {
      try {
        setContactsLoading(true);

        const [groups, currentUser] = await Promise.all([
          getMyGroups(),
          getCurrentUser().catch(() => null),
        ]);

        const memberEntries = await Promise.all(
          groups.map(async (group) => ({
            groupTitle: group.title,
            members: await getGroupMembers(group.id).catch(() => []),
          })),
        );

        const contactsMap = new Map<
          string,
          {
            member: BackendGroupMember;
            groupTitles: Set<string>;
            sharedGroupCount: number;
          }
        >();

        memberEntries.forEach(({ groupTitle, members }) => {
          members.forEach((member) => {
            if (isCurrentUserMember(member, currentUser)) return;

            const key = getMemberLookupKey(member);
            if (!key) return;

            const existing = contactsMap.get(key);

            if (existing) {
              existing.sharedGroupCount += 1;
              if (groupTitle) existing.groupTitles.add(groupTitle);
              if (shouldReplaceMemberCandidate(existing.member, member)) {
                existing.member = member;
              }
              return;
            }

            contactsMap.set(key, {
              member,
              groupTitles: new Set(groupTitle ? [groupTitle] : []),
              sharedGroupCount: 1,
            });
          });
        });

        const nextContacts = Array.from(contactsMap.values())
          .map((entry, index) =>
            makeContactFromMember(
              entry.member,
              index,
              entry.sharedGroupCount,
              Array.from(entry.groupTitles),
            ),
          )
          .sort((left, right) => {
            if (right.sharedGroupCount !== left.sharedGroupCount) {
              return right.sharedGroupCount - left.sharedGroupCount;
            }

            return left.name.localeCompare(right.name, 'fa');
          });

        if (!ignore) setContacts(nextContacts);
      } catch {
        if (!ignore) setContacts([]);
      } finally {
        if (!ignore) setContactsLoading(false);
      }
    }

    void loadContacts();

    return () => {
      ignore = true;
    };
  }, []);

  const selectedContacts = useMemo(
    () => contacts.filter((contact) => selectedIds.includes(contact.id)),
    [contacts, selectedIds],
  );

  function updateField<K extends keyof GroupValues>(field: K, value: GroupValues[K]) {
    setValues((prev) => ({ ...prev, [field]: value }));

    setErrors((prev) => {
      const fieldHasError =
        field === 'name'
          ? Boolean(prev.name)
          : field === 'groupType'
            ? Boolean(prev.groupType)
            : false;

      if (!fieldHasError && !prev.form) return prev;

      const nextValues = { ...values, [field]: value };
      return validateGroupInfo(nextValues);
    });
  }

  function goNext() {
    const validation = validateGroupInfo(values);

    if (validation.name || validation.groupType) {
      setErrors(validation);
      return;
    }

    setErrors({});
    setCurrentStep(2);
  }

  function handleToggleMember(id: string) {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    );
  }

  function handleFinish() {
    const validation = validateGroupInfo(values);

    if (validation.name || validation.groupType) {
      setErrors(validation);
      setCurrentStep(1);
      return;
    }

    onComplete({
      name: values.name.trim(),
      description: values.description.trim(),
      groupType: values.groupType,
      memberCount: selectedIds.length,
      selectedUserIds: selectedContacts.map((member) => member.userId || '').filter(Boolean),
      selectedPhones: selectedContacts
        .map((member) => normalizePhone(member.phone))
        .filter(Boolean),
      selectedEmails: selectedContacts
        .map((member) => normalizeText(member.email))
        .filter(Boolean),
    });
  }

  return (
    <main className="create-group-wizard-page px-4 py-4 sm:px-6 sm:py-5 xl:px-8" dir="rtl">
      <div className="mx-auto max-w-[980px] space-y-4">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="text-right">
            <button
              type="button"
              onClick={onBack}
              className="mb-3 inline-flex items-center gap-2 rounded-full bg-white px-3 py-1.5 text-xs font-extrabold text-slate-600 shadow-sm transition hover:bg-slate-50 hover:text-text"
            >
              <ArrowLeft className="h-4 w-4" />
              بازگشت به گروه‌ها
            </button>

            <h1 className="text-[30px] font-extrabold leading-tight tracking-[-0.03em] text-text sm:text-[34px]">
              تشکیل گروه جدید
            </h1>

            <p className="mt-1.5 text-sm font-semibold leading-7 text-muted">
              دو قدم ساده: اطلاعات گروه، بعد اعضا.
            </p>
          </div>

          <div className="rounded-[18px] border border-emerald-100 bg-emerald-50 px-4 py-3 text-right text-sm font-extrabold text-emerald-700">
            {currentStep === 1 ? 'اول اسم و نوع گروه' : 'اعضا اختیاری‌اند'}
          </div>
        </header>

        <CompactStepper currentStep={currentStep} />

        <section className="rounded-[32px] border-2 border-slate-200 bg-white/60 p-3 shadow-[0_18px_46px_rgba(15,23,42,0.055)] sm:p-4">
          <div className="rounded-[26px] bg-white p-4 sm:p-5">
            {currentStep === 1 ? (
              <GroupInfoStep values={values} errors={errors} onChange={updateField} />
            ) : (
              <MembersStep
                contacts={contacts}
                contactsLoading={contactsLoading}
                selectedIds={selectedIds}
                searchValue={searchValue}
                onSearchChange={setSearchValue}
                onToggleMember={handleToggleMember}
              />
            )}
          </div>

          <div className="mt-3 flex flex-col-reverse gap-3 px-1 pb-1 sm:flex-row sm:items-center sm:justify-between">
            <button
              type="button"
              onClick={currentStep === 1 ? onBack : () => setCurrentStep(1)}
              className="inline-flex h-12 items-center justify-center rounded-[18px] border border-slate-200 bg-white px-6 text-sm font-extrabold text-slate-600 transition hover:bg-slate-50"
            >
              {currentStep === 1 ? 'انصراف' : 'مرحله قبل'}
            </button>

            <button
              type="button"
              onClick={currentStep === 1 ? goNext : handleFinish}
              className="inline-flex h-12 items-center justify-center gap-2 rounded-[18px] bg-gradient-to-l from-[#00915F] to-[#00A86B] px-6 text-sm font-extrabold text-white shadow-[0_14px_30px_rgba(0,168,107,0.22)] transition hover:-translate-y-0.5"
            >
              {currentStep === 1 ? (
                <>
                  مرحله بعدی
                  <ChevronLeft className="h-4 w-4" />
                </>
              ) : (
                <>
                  ساخت گروه
                  <Check className="h-4 w-4" />
                </>
              )}
            </button>
          </div>
        </section>
      </div>
    </main>
  );
}