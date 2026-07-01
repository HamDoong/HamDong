import { useEffect, useMemo, useRef, useState, type RefObject } from 'react';
import {
  ArrowRight,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronUp,
  CircleHelp,
  FileText,
  Home,
  ImageUp,
  Loader2,
  Plane,
  Search,
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
import { getCurrentUser, searchUsersByArtName, type CurrentUser } from '../lib/userApi';

export type GroupTypeValue = '' | 'travel' | 'food' | 'home' | 'other';

export interface CreatedGroupPayload {
  name: string;
  description: string;
  groupType: GroupTypeValue;
  memberCount: number;
  selectedUserIds?: string[];
  selectedPhones?: string[];
  selectedEmails?: string[];
  selectedRecipients?: Array<{ userId?: string; email?: string }>;
  receiptFile?: File;
}

interface CreateGroupWizardProps {
  onBack: () => void;
  onComplete: (payload: CreatedGroupPayload) => void | Promise<void>;
}

interface Contact {
  id: string;
  name: string;
  phone: string;
  email?: string;
  userId?: string;
  username?: string;
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
  icon: typeof Plane;
}> = [
  {
    value: 'travel',
    label: 'سفر',
    icon: Plane,
  },
  {
    value: 'food',
    label: 'غذا',
    icon: UtensilsCrossed,
  },
  {
    value: 'home',
    label: 'خانه',
    icon: Home,
  },
  {
    value: 'other',
    label: 'سایر',
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
  return (phone || '')
    .replace(/[۰-۹]/g, (digit) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(digit)))
    .replace(/[٠-٩]/g, (digit) => String('٠١٢٣٤٥٦٧٨٩'.indexOf(digit)))
    .replace(/[^\d+]/g, '')
    .trim();
}

function normalizeText(value?: string | null) {
  return (value || '')
    .trim()
    .replace(/ي/g, 'ی')
    .replace(/ك/g, 'ک')
    .replace(/[\u064B-\u065F\u0670]/g, '')
    .replace(/\s+/g, ' ')
    .toLowerCase();
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

function getMemberUsername(member: BackendGroupMember) {
  return [
    member.art_name,
    member.username,
    member.user?.art_name,
    member.user?.username,
    member.profile?.art_name,
    member.profile?.username,
  ].find((value) => typeof value === 'string' && value.trim())?.trim();
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
  _groupTitles: string[],
): Contact {
  const name = getMemberName(member);
  const phone = getMemberPhone(member);

  const sourceLabel =
    sharedGroupCount > 0
      ? `${toPersianNumber(sharedGroupCount)} گروه مشترک`
      : 'عضو گروه‌های قبلی';

  return {
    id: getMemberLookupKey(member) || String(index),
    name,
    phone,
    email: getMemberEmail(member) || undefined,
    userId: getMemberUserId(member) || undefined,
    username: getMemberUsername(member),
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
    <nav className="create-group-stepper rounded-[20px] border border-slate-200 bg-white/80 px-4 py-3" aria-label="مراحل ساخت گروه">
      <div className="text-xs font-extrabold">
        <span className="text-emerald-700">مرحله {toPersianNumber(currentStep)} از ۲</span>
      </div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-100" aria-hidden="true">
        <div
          className="h-full rounded-full bg-emerald-600 transition-[width] duration-300"
          style={{ width: currentStep === 1 ? '50%' : '100%' }}
        />
      </div>
      <div className="mt-2 grid grid-cols-2 text-[11px] font-bold text-muted" aria-hidden="true">
        <span className={currentStep >= 1 ? 'text-emerald-700' : undefined}>۱. اطلاعات گروه</span>
        <span className={cn('text-left', currentStep === 2 && 'text-emerald-700')}>۲. اعضا</span>
      </div>
    </nav>
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
  descriptionOpen,
  nameInputRef,
  groupTypeRef,
  receiptFile,
  receiptError,
  onChange,
  onDescriptionToggle,
  onReceiptChange,
}: {
  values: GroupValues;
  errors: GroupInfoErrors;
  descriptionOpen: boolean;
  nameInputRef: RefObject<HTMLInputElement>;
  groupTypeRef: RefObject<HTMLDivElement>;
  receiptFile: File | null;
  receiptError?: string;
  onChange: <K extends keyof GroupValues>(field: K, value: GroupValues[K]) => void;
  onDescriptionToggle: () => void;
  onReceiptChange: (file: File | null) => void;
}) {
  const receiptInputRef = useRef<HTMLInputElement>(null);

  return (
    <section className="space-y-5">
      <div className="text-right">
        <h2 className="text-[25px] font-extrabold tracking-[-0.03em] text-text">
          اطلاعات گروه
        </h2>
      </div>

      <FormError message={errors.form} />

      <div className="space-y-6">
        <label className="block text-right" htmlFor="group-name">
          <span className="mb-2 block text-sm font-extrabold text-text">نام گروه</span>
          <input
            ref={nameInputRef}
            id="group-name"
            dir="rtl"
            autoFocus
            value={values.name}
            onChange={(event) => onChange('name', event.target.value)}
            placeholder="مثلاً سفر شمال، خانه، شام جمعه..."
            aria-invalid={Boolean(errors.name)}
            aria-describedby={errors.name ? 'group-name-error' : undefined}
            className={cn(
              'h-12 w-full rounded-[16px] border bg-slate-50/70 px-4 text-sm font-bold text-text outline-none transition placeholder:font-semibold placeholder:text-slate-400 focus:bg-white focus:ring-4',
              errors.name
                ? 'border-rose-200 focus:border-rose-300 focus:ring-rose-500/10'
                : 'border-slate-200 focus:border-emerald-300 focus:ring-emerald-500/10',
            )}
          />
          {errors.name ? (
            <span id="group-name-error" className="mt-2 block text-xs font-bold text-rose-500">{errors.name}</span>
          ) : null}
        </label>

        <div ref={groupTypeRef} tabIndex={-1} className="border-t border-slate-100 pt-5 outline-none">
          <div className="mb-3 flex items-center justify-between gap-3 text-right">
          <div>
            <h3 className="text-base font-extrabold text-text">نوع گروه</h3>
          </div>

          {errors.groupType ? (
            <span className="rounded-full bg-rose-50 px-3 py-1 text-xs font-extrabold text-rose-500">
              انتخاب کن
            </span>
          ) : null}
        </div>

          <div className="grid grid-cols-2 gap-2.5 lg:grid-cols-4" role="group" aria-label="انتخاب نوع گروه">
          {groupTypeOptions.map((option) => {
            const Icon = option.icon;
            const selected = values.groupType === option.value;

            return (
              <button
                key={option.value}
                type="button"
                onClick={() => onChange('groupType', option.value)}
                aria-pressed={selected}
                className={cn(
                    'flex min-h-[68px] items-center justify-between gap-2 rounded-[18px] border px-3 py-2 text-right transition',
                  selected
                      ? 'border-emerald-400 bg-emerald-50 text-emerald-700 ring-2 ring-emerald-500/10'
                    : 'border-slate-200 bg-white text-slate-700 hover:border-emerald-200 hover:bg-emerald-50/40',
                )}
              >
                  <div className="flex min-w-0 items-center gap-2.5">
                  <span
                    className={cn(
                        'flex h-9 w-9 shrink-0 items-center justify-center rounded-[13px]',
                      selected ? 'bg-emerald-600 text-white' : 'bg-slate-50 text-emerald-600',
                    )}
                  >
                      <Icon className="h-4.5 w-4.5" />
                  </span>
                    <span className="truncate text-sm font-extrabold">{option.label}</span>
                  </div>
                  <span
                    className={cn(
                      'flex h-5 w-5 shrink-0 items-center justify-center rounded-full border',
                      selected
                        ? 'border-emerald-600 bg-emerald-600 text-white'
                        : 'border-slate-200 bg-white text-transparent',
                    )}
                  >
                    <Check className="h-3.5 w-3.5" />
                  </span>
              </button>
            );
          })}
          </div>
          {errors.groupType ? (
            <span className="mt-2 block text-xs font-bold text-rose-500">{errors.groupType}</span>
          ) : null}
        </div>

        <div className="grid gap-3 border-t border-slate-100 pt-5 sm:grid-cols-2">
          <div className={cn('rounded-[18px] border p-3 transition', descriptionOpen ? 'border-emerald-200 bg-emerald-50/40' : 'border-slate-200 bg-slate-50/60 hover:border-emerald-300')}>
          <button
            type="button"
            onClick={onDescriptionToggle}
              className="flex min-h-12 w-full items-center justify-between gap-3 text-right text-sm font-extrabold text-text transition hover:text-emerald-700"
            aria-expanded={descriptionOpen}
          >
              <span className="flex items-center gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[14px] bg-emerald-100 text-emerald-700"><FileText className="h-5 w-5" /></span>
                <span><span className="block">افزودن توضیحات</span><span className="mt-0.5 block text-[11px] font-semibold text-muted">اختیاری</span></span>
              </span>
            {descriptionOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>

          {descriptionOpen ? <label className="mt-2 block text-right" htmlFor="group-description">
          <div className="mb-2 flex items-center justify-end gap-3">
            <span className="text-xs font-bold text-slate-400">
              {toPersianNumber(values.description.length)}/۳۰۰
            </span>
          </div>

          <textarea
              id="group-description"
            dir="rtl"
            value={values.description}
            onChange={(event) => onChange('description', event.target.value.slice(0, 300))}
            placeholder="مثلاً هزینه‌های سفر ۴ روزه شمال"
              className="min-h-[88px] w-full resize-none rounded-[16px] border border-slate-200 bg-slate-50/70 px-4 py-3 text-sm font-semibold leading-7 text-text outline-none transition placeholder:text-slate-400 focus:border-emerald-300 focus:bg-white focus:ring-4 focus:ring-emerald-500/10"
          />
          </label> : null}
          </div>

          <div className={cn('create-group-upload-card rounded-[18px] border p-3 transition', receiptError ? 'border-rose-300 bg-rose-50/50' : receiptFile ? 'border-emerald-300 bg-emerald-50/50' : 'border-dashed border-slate-300 bg-slate-50/60 hover:border-emerald-300')}>
            <input
              ref={receiptInputRef}
              type="file"
              className="sr-only"
              accept="image/jpeg,image/png,image/webp,application/pdf"
              onChange={(event) => {
                onReceiptChange(event.target.files?.[0] || null);
                event.target.value = '';
              }}
            />
            <button
              type="button"
              onClick={() => receiptInputRef.current?.click()}
              className="flex min-h-12 w-full items-center justify-between gap-3 text-right"
            >
              <span className="flex min-w-0 items-center gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[14px] bg-sky-100 text-sky-700"><ImageUp className="h-5 w-5" /></span>
                <span className="min-w-0">
                  <span className="block truncate text-sm font-extrabold text-text">{receiptFile ? receiptFile.name : 'افزودن فاکتور یا رسید'}</span>
                  <span className="mt-0.5 block text-[11px] font-semibold text-muted">اختیاری · تصویر یا PDF تا ۵ مگابایت</span>
                </span>
              </span>
              <span className="shrink-0 text-xs font-extrabold text-emerald-700">{receiptFile ? 'تغییر' : 'انتخاب'}</span>
            </button>
            {receiptFile ? (
              <button type="button" onClick={() => onReceiptChange(null)} className="mt-2 inline-flex h-9 items-center gap-1 rounded-full bg-white px-3 text-xs font-bold text-rose-600 shadow-sm">
                <X className="h-3.5 w-3.5" /> حذف فایل
              </button>
            ) : null}
            {receiptError ? <p className="mt-2 text-xs font-bold text-rose-600">{receiptError}</p> : null}
          </div>
        </div>
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
      aria-pressed={selected}
      className={cn(
        'flex min-h-[72px] w-full items-center justify-between gap-3 px-3 py-2.5 text-right transition sm:px-4',
        selected
          ? 'bg-emerald-50/90'
          : 'bg-white hover:bg-slate-50',
      )}
    >
      <div className="flex min-w-0 items-center gap-3">
        <Avatar label={contact.avatar} className={contact.avatarClass} />

        <div className="min-w-0 text-right">
          <div className="truncate text-sm font-extrabold text-text">{contact.name}</div>
          <div className="mt-1 flex min-w-0 items-center gap-2 text-xs font-semibold text-muted">
            <span className="truncate">{contact.username ? `@${contact.username}` : contact.phone || 'شماره ثبت نشده'}</span>
            {contact.sourceLabel ? <><span aria-hidden="true">·</span><span className="shrink-0 text-emerald-600">{contact.sourceLabel}</span></> : null}
          </div>
        </div>
      </div>

      <span
        className={cn(
          'flex h-7 w-7 shrink-0 items-center justify-center rounded-full border',
          selected
            ? 'border-emerald-600 bg-emerald-600 text-white'
            : 'border-slate-200 bg-slate-50 text-slate-300',
        )}
      >
        {selected ? <Check className="h-4 w-4" /> : null}
      </span>
    </button>
  );
}

function MembersStep({
  contacts,
  contactsLoading,
  userSearchLoading,
  userSearchError,
  selectedIds,
  searchValue,
  onSearchChange,
  onToggleMember,
}: {
  contacts: Contact[];
  contactsLoading: boolean;
  userSearchLoading: boolean;
  userSearchError: string;
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
      normalizeText(contact.username).includes(normalizedSearch.replace(/^@/, '')) ||
      normalizePhone(contact.phone).includes(normalizedSearch) ||
      normalizeText(contact.email).includes(normalizedSearch)
    );
  });

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 text-right sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-[25px] font-extrabold tracking-[-0.03em] text-text">
            اعضای گروه
          </h2>
        </div>

        <div className="w-fit rounded-full border border-emerald-100 bg-emerald-50 px-3 py-1.5 text-right text-xs font-extrabold text-emerald-700" aria-live="polite">
          {toPersianNumber(selectedContacts.length)} نفر انتخاب شده
        </div>
      </div>

      <div>
        <div className="relative">
          <Search className="pointer-events-none absolute right-4 top-1/2 h-4 w-4 -translate-y-1/2 text-emerald-600" />

          <input
            type="search"
            dir="rtl"
            value={searchValue}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="نام یا نام کاربری را جستجو کن..."
            aria-label="جستجوی کاربر با نام یا نام کاربری"
            className="h-12 w-full rounded-[16px] border border-slate-200 bg-slate-50/70 pr-11 pl-11 text-sm font-bold text-text outline-none transition placeholder:font-semibold placeholder:text-slate-400 focus:border-emerald-300 focus:bg-white focus:ring-4 focus:ring-emerald-500/10"
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
        <div className="mt-2 flex min-h-5 items-center gap-2 px-1 text-[11px] font-semibold text-muted" aria-live="polite">
          {userSearchLoading ? <><Loader2 className="h-3.5 w-3.5 animate-spin text-emerald-600" /> در حال جستجوی نام کاربری...</> : userSearchError ? <span className="text-rose-600">{userSearchError}</span> : <span>برای جستجوی سراسری نام کاربری، حداقل ۲ حرف بنویس.</span>}
        </div>
      </div>

      {selectedContacts.length > 0 ? (
        <div className="flex gap-2 overflow-x-auto pb-1" aria-label="اعضای انتخاب‌شده">
            {selectedContacts.map((contact) => (
              <button
                key={contact.id}
                type="button"
                onClick={() => onToggleMember(contact.id)}
                className="flex min-h-10 shrink-0 items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 py-1 pr-1 pl-3 text-xs font-extrabold text-emerald-800 transition hover:bg-rose-50 hover:text-rose-600"
                aria-label={`حذف ${contact.name} از اعضای انتخاب‌شده`}
              >
                <span className={cn('flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br text-xs text-white', contact.avatarClass)}>{contact.avatar}</span>
                <span>{contact.name}</span>
                <X className="h-3.5 w-3.5" />
              </button>
            ))}
        </div>
      ) : null}

      <div className="overflow-hidden rounded-[20px] border border-slate-200 bg-white">
        {contactsLoading ? (
          <div className="flex items-center justify-center gap-2 bg-slate-50 p-8 text-center text-sm font-bold text-muted">
            <Loader2 className="h-4 w-4 animate-spin" />
            در حال دریافت اعضای قبلی...
          </div>
        ) : null}

        {!contactsLoading && !userSearchLoading && contacts.length === 0 ? (
          <div className="bg-slate-50/70 p-8 text-center">
            <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-[22px] bg-white text-emerald-600 shadow-sm">
              <CircleHelp className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-extrabold text-text">فعلاً عضو پیشنهادی نداریم</h3>
            <p className="mx-auto mt-2 max-w-[420px] text-sm font-semibold leading-7 text-muted">
              مشکلی نیست. گروه رو بساز؛ بعداً از داخل گروه لینک دعوت می‌سازی.
            </p>
          </div>
        ) : null}

        {!contactsLoading && !userSearchLoading && contacts.length > 0 && visibleContacts.length === 0 ? (
          <div className="bg-slate-50/70 p-8 text-center text-sm font-semibold text-muted">
            نتیجه‌ای پیدا نشد. جستجو رو ساده‌تر کن.
          </div>
        ) : null}

        <div className="max-h-[420px] divide-y divide-slate-100 overflow-y-auto overscroll-auto">
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
  const [userSearchLoading, setUserSearchLoading] = useState(false);
  const [userSearchError, setUserSearchError] = useState('');
  const [descriptionOpen, setDescriptionOpen] = useState(false);
  const [receiptFile, setReceiptFile] = useState<File | null>(null);
  const [receiptError, setReceiptError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const nameInputRef = useRef<HTMLInputElement>(null);
  const groupTypeRef = useRef<HTMLDivElement>(null);

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

        if (!ignore) {
          setContacts((previous) => {
            const searchedContacts = previous.filter((contact) => contact.sharedGroupCount === 0);
            const knownUserIds = new Set(nextContacts.map((contact) => contact.userId).filter(Boolean));
            return [
              ...nextContacts,
              ...searchedContacts.filter((contact) => !contact.userId || !knownUserIds.has(contact.userId)),
            ];
          });
        }
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

  useEffect(() => {
    const query = searchValue.trim().replace(/^@/, '');

    if (currentStep !== 2 || query.length < 2) {
      setUserSearchLoading(false);
      setUserSearchError('');
      return;
    }

    let ignore = false;
    const timeoutId = window.setTimeout(async () => {
      try {
        setUserSearchLoading(true);
        setUserSearchError('');
        const results = await searchUsersByArtName(query, 12);

        if (ignore) return;

        setContacts((previous) => {
          const next = [...previous];

          results.forEach((result, index) => {
            const existingIndex = next.findIndex((contact) => contact.userId === result.user_id);

            if (existingIndex >= 0) {
              next[existingIndex] = { ...next[existingIndex], username: result.art_name };
              return;
            }

            next.push({
              id: result.user_id,
              name: result.art_name,
              username: result.art_name,
              phone: '',
              userId: result.user_id,
              avatar: result.art_name.slice(0, 1) || '؟',
              avatarClass: avatarGradients[(previous.length + index) % avatarGradients.length],
              sharedGroupCount: 0,
              sourceLabel: 'نتیجه جستجوی نام کاربری',
            });
          });

          return next;
        });
      } catch {
        if (!ignore) setUserSearchError('جستجوی نام کاربری انجام نشد؛ دوباره تلاش کن.');
      } finally {
        if (!ignore) setUserSearchLoading(false);
      }
    }, 350);

    return () => {
      ignore = true;
      window.clearTimeout(timeoutId);
    };
  }, [currentStep, searchValue]);

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
      requestAnimationFrame(() => {
        if (validation.name) nameInputRef.current?.focus();
        else groupTypeRef.current?.focus();
      });
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

  function handleReceiptChange(file: File | null) {
    setReceiptError('');

    if (!file) {
      setReceiptFile(null);
      return;
    }

    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp', 'application/pdf'];
    const allowedExtension = /\.(jpe?g|png|webp|pdf)$/i.test(file.name);

    if (file.size > 5 * 1024 * 1024) {
      setReceiptFile(null);
      setReceiptError('حجم فایل باید کمتر از ۵ مگابایت باشد.');
      return;
    }

    if (!allowedTypes.includes(file.type) && !allowedExtension) {
      setReceiptFile(null);
      setReceiptError('فقط فایل JPG، PNG، WEBP یا PDF مجاز است.');
      return;
    }

    setReceiptFile(file);
  }

  async function handleFinish() {
    if (submitting) return;

    const validation = validateGroupInfo(values);

    if (validation.name || validation.groupType) {
      setErrors(validation);
      setCurrentStep(1);
      requestAnimationFrame(() => nameInputRef.current?.focus());
      return;
    }

    try {
      setSubmitting(true);
      await onComplete({
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
        selectedRecipients: selectedContacts
          .map((member) => ({
            userId: member.userId || undefined,
            email: normalizeText(member.email) || undefined,
          }))
          .filter((recipient) => Boolean(recipient.userId || recipient.email)),
        receiptFile: receiptFile || undefined,
      });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="create-group-wizard-page px-3 py-3 sm:px-6 sm:py-5 xl:px-8" dir="rtl">
      <div className="mx-auto max-w-[860px] space-y-4">
        <header className="flex items-center gap-3 text-right">
            <button
              type="button"
              onClick={onBack}
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[16px] border border-slate-200 bg-white text-slate-600 shadow-sm transition hover:bg-slate-50 hover:text-text"
              aria-label="بازگشت به گروه‌ها"
            >
              <ArrowRight className="h-5 w-5" />
            </button>

          <div className="min-w-0">
            <h1 className="text-base font-extrabold text-text sm:text-lg">
              ساخت گروه
            </h1>

          </div>
        </header>

        <CompactStepper currentStep={currentStep} />

        <section className="panel-surface rounded-[24px] border border-slate-200 bg-white p-4 shadow-[0_14px_36px_rgba(15,23,42,0.05)] sm:p-6">
          <div>
            {currentStep === 1 ? (
              <GroupInfoStep
                values={values}
                errors={errors}
                descriptionOpen={descriptionOpen}
                nameInputRef={nameInputRef}
                groupTypeRef={groupTypeRef}
                receiptFile={receiptFile}
                receiptError={receiptError}
                onChange={updateField}
                onDescriptionToggle={() => setDescriptionOpen((prev) => !prev)}
                onReceiptChange={handleReceiptChange}
              />
            ) : (
              <MembersStep
                contacts={contacts}
                contactsLoading={contactsLoading}
                userSearchLoading={userSearchLoading}
                userSearchError={userSearchError}
                selectedIds={selectedIds}
                searchValue={searchValue}
                onSearchChange={setSearchValue}
                onToggleMember={handleToggleMember}
              />
            )}
          </div>

          <div className="create-group-actions sticky bottom-2 z-20 mt-6 grid grid-cols-[minmax(0,0.72fr)_minmax(0,1.28fr)] gap-2 rounded-[18px] border border-slate-200 bg-white/95 p-2 shadow-[0_12px_34px_rgba(15,23,42,0.14)] backdrop-blur sm:static sm:flex sm:items-center sm:justify-between sm:border-0 sm:bg-transparent sm:p-0 sm:shadow-none">
            <button
              type="button"
              onClick={currentStep === 1 ? onBack : () => setCurrentStep(1)}
              disabled={submitting}
              className="inline-flex h-12 items-center justify-center rounded-[14px] border border-slate-200 bg-white px-4 text-sm font-extrabold text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60 sm:rounded-[16px] sm:px-6"
            >
              {currentStep === 1 ? 'انصراف' : 'مرحله قبل'}
            </button>

            <button
              type="button"
              onClick={currentStep === 1 ? goNext : () => void handleFinish()}
              disabled={submitting}
              className="inline-flex h-12 items-center justify-center gap-2 rounded-[14px] bg-gradient-to-l from-[#00915F] to-[#00A86B] px-4 text-sm font-extrabold text-white shadow-[0_12px_26px_rgba(0,168,107,0.2)] transition hover:-translate-y-0.5 disabled:cursor-wait disabled:opacity-70 sm:rounded-[16px] sm:px-6"
            >
              {currentStep === 1 ? (
                <>
                  ادامه؛ انتخاب اعضا
                  <ChevronLeft className="h-4 w-4" />
                </>
              ) : (
                <>
                  {submitting ? 'در حال ساخت...' : selectedIds.length > 0 ? `ساخت با ${toPersianNumber(selectedIds.length)} عضو` : 'ساخت گروه'}
                  {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                </>
              )}
            </button>
          </div>
        </section>
      </div>
    </main>
  );
}
