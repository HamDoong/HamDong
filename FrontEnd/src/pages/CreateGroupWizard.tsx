import { useEffect, useMemo, useState } from 'react';
import {
  ArrowLeft,
  Check,
  ChevronLeft,
  Info,
  Search,
  UserPlus,
  Users,
  X,
} from 'lucide-react';
import { CreateGroupStepper } from '../components/create-group/CreateGroupStepper';
import {
  GroupInfoStep,
  type GroupInfoValues,
  type GroupTypeValue,
} from '../components/create-group/GroupInfoStep';
import {
  getGroupMembers,
  getMyGroups,
  type BackendGroupMember,
} from '../lib/groupApi';
import { getCurrentUser } from '../lib/userApi';

export interface CreatedGroupPayload {
  name: string;
  description: string;
  groupType: GroupTypeValue;
  memberCount: number;
  selectedPhones?: string[];
}

interface CreateGroupWizardProps {
  onBack: () => void;
  onComplete: (payload: CreatedGroupPayload) => void;
}

interface Contact {
  id: string;
  name: string;
  phone: string;
  isFriend: boolean;
  isFrequent: boolean;
  avatar: string;
  avatarClass: string;
  sourceLabel?: string;
}

type ContactFilter = 'all' | 'friends' | 'frequent';
type WizardStep = 1 | 2;

const steps = [
  { id: 1, label: 'اطلاعات گروه' },
  { id: 2, label: 'اعضای پیشنهادی' },
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

function normalizePhone(phone?: string | null) {
  return (phone || '').replace(/\s+/g, '').trim();
}

function getMemberUserId(member: BackendGroupMember) {
  return member.user_id || member.id || member.member_id || '';
}

function getMemberName(member: BackendGroupMember) {
  return member.display_name || member.full_name || member.phone_number || member.phone || 'عضو گروه';
}

function getMemberPhone(member: BackendGroupMember) {
  return member.phone_number || member.phone || '';
}

function makeContactFromMember(member: BackendGroupMember, index: number): Contact {
  const name = getMemberName(member);
  const phone = getMemberPhone(member);
  const fallbackId = normalizePhone(phone) || getMemberUserId(member) || String(index);

  return {
    id: fallbackId,
    name,
    phone: phone || 'شماره ثبت نشده',
    isFriend: true,
    isFrequent: index < 6,
    avatar: name.slice(0, 1),
    avatarClass: avatarGradients[index % avatarGradients.length],
    sourceLabel: 'عضو گروه‌های قبلی',
  };
}

function Avatar({ label, className }: { label: string; className: string }) {
  return (
    <div className={cn('flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br text-sm font-bold text-white shadow-sm', className)}>
      {label}
    </div>
  );
}

function SummaryCard({ values, memberCount }: { values: GroupInfoValues; memberCount: number }) {
  const groupTypeLabel = (() => {
    switch (values.groupType) {
      case 'travel':
        return 'سفر';
      case 'food':
        return 'غذا و رستوران';
      case 'home':
        return 'خانه و زندگی';
      case 'other':
        return 'سایر';
      default:
        return '-';
    }
  })();

  return (
    <aside className="panel-surface order-2 p-6 xl:order-2">
      <div className="mb-8 flex items-center justify-between">
        <h3 className="text-[28px] font-bold tracking-[-0.03em] text-text">خلاصه گروه</h3>
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600">
          <Users className="h-5 w-5" strokeWidth={1.9} />
        </div>
      </div>

      <div className="space-y-8">
        <div className="space-y-2 text-right"><div className="text-sm text-muted">نام گروه</div><div className="text-lg font-semibold text-text">{values.name || '-'}</div></div>
        <div className="space-y-2 text-right"><div className="text-sm text-muted">نوع گروه</div><div className="text-lg font-semibold text-text">{groupTypeLabel}</div></div>
        <div className="space-y-2 text-right"><div className="text-sm text-muted">اعضای پیشنهادی</div><div className="text-lg font-semibold text-text">{memberCount.toLocaleString('fa-IR')} نفر</div></div>
      </div>

      <div className="mt-10 rounded-[20px] border border-emerald-100 bg-emerald-50/50 p-4">
        <div className="mb-3 flex items-center gap-2 text-emerald-600"><Info className="h-4.5 w-4.5" /><span className="text-sm font-semibold">اطلاع‌رسانی</span></div>
        <p className="text-sm leading-7 text-slate-600">
          این مرحله فقط اطلاعات گروه را ثبت می‌کند. هزینه‌ها و لینک دعوت بعد از ورود به صفحه جزئیات گروه مدیریت می‌شوند.
        </p>
      </div>
    </aside>
  );
}

function AddMembersStep({
  contactsList,
  contactsLoading,
  searchValue,
  filter,
  selectedIds,
  manualPhone,
  manualPhones,
  onSearchChange,
  onFilterChange,
  onToggleMember,
  onRemoveMember,
  onManualPhoneChange,
  onAddManualPhone,
  onRemoveManualPhone,
}: {
  contactsList: Contact[];
  contactsLoading: boolean;
  searchValue: string;
  filter: ContactFilter;
  selectedIds: string[];
  manualPhone: string;
  manualPhones: string[];
  onSearchChange: (value: string) => void;
  onFilterChange: (value: ContactFilter) => void;
  onToggleMember: (id: string) => void;
  onRemoveMember: (id: string) => void;
  onManualPhoneChange: (value: string) => void;
  onAddManualPhone: () => void;
  onRemoveManualPhone: (phone: string) => void;
}) {
  const selectedMembers = contactsList.filter((member) => selectedIds.includes(member.id));

  const filteredContacts = contactsList.filter((contact) => {
    const matchesSearch = !searchValue || contact.name.includes(searchValue) || contact.phone.includes(searchValue);
    const matchesFilter = filter === 'all' ? true : filter === 'friends' ? contact.isFriend : contact.isFrequent;
    return matchesSearch && matchesFilter;
  });

  const counts = {
    all: contactsList.length,
    friends: contactsList.filter((item) => item.isFriend).length,
    frequent: contactsList.filter((item) => item.isFrequent).length,
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col items-start justify-between gap-3 border-b border-border/80 pb-6 lg:flex-row lg:items-center">
        <div className="text-right">
          <h2 className="text-[28px] font-bold tracking-[-0.03em] text-text">اعضای پیشنهادی</h2>
          <p className="mt-2 text-sm text-muted">
            این لیست از اعضای واقعی گروه‌های قبلی شما ساخته می‌شود؛ داده رندوم حذف شده است.
          </p>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)]">
        <div className="rounded-[24px] border border-border bg-white p-5">
          <div className="mb-5 flex items-center justify-between">
            <h3 className="text-[22px] font-bold text-text">افراد انتخاب شده</h3>
            <span className="inline-flex h-8 min-w-[32px] items-center justify-center rounded-full bg-emerald-50 px-2 text-sm font-bold text-emerald-600">
              {selectedMembers.length + manualPhones.length}
            </span>
          </div>

          <div className="space-y-3">
            {selectedMembers.length === 0 && manualPhones.length === 0 ? (
              <div className="rounded-[18px] border border-dashed border-border px-4 py-8 text-center text-sm leading-7 text-muted">
                هنوز عضوی انتخاب نشده است. این انتخاب‌ها فعلاً برای آماده‌سازی دعوت بعد از ساخت گروه هستند.
              </div>
            ) : null}

            {selectedMembers.map((member) => (
              <div key={member.id} className="flex items-center justify-between rounded-[18px] border border-border bg-white px-4 py-3">
                <div className="flex min-w-0 items-center gap-3">
                  <Avatar label={member.avatar} className={member.avatarClass} />
                  <div className="min-w-0 text-right"><div className="truncate text-base font-semibold text-text">{member.name}</div><div className="text-xs text-muted">{member.phone}</div></div>
                </div>
                <button type="button" onClick={() => onRemoveMember(member.id)} className="flex h-9 w-9 items-center justify-center rounded-full text-slate-500 transition hover:bg-slate-100 hover:text-rose-500"><X className="h-4.5 w-4.5" /></button>
              </div>
            ))}

            {manualPhones.map((phone) => (
              <div key={phone} className="flex items-center justify-between rounded-[18px] border border-emerald-100 bg-emerald-50/60 px-4 py-3">
                <div className="text-right"><div className="text-base font-semibold text-text">شماره پیشنهادی برای دعوت</div><div className="text-xs text-muted">{phone}</div></div>
                <button type="button" onClick={() => onRemoveManualPhone(phone)} className="flex h-9 w-9 items-center justify-center rounded-full text-slate-500 transition hover:bg-white hover:text-rose-500"><X className="h-4.5 w-4.5" /></button>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-[24px] border border-border bg-white p-5">
          <div className="mb-5">
            <div className="relative">
              <Search className="pointer-events-none absolute right-4 top-1/2 h-4.5 w-4.5 -translate-y-1/2 text-slate-400" />
              <input dir="rtl" value={searchValue} onChange={(event) => onSearchChange(event.target.value)} placeholder="جستجو با نام یا شماره موبایل..." className="h-12 w-full rounded-[16px] border border-border bg-white pr-11 pl-4 text-sm text-text outline-none transition placeholder:text-slate-400 focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10" />
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              {[
                { id: 'all', label: 'همه', count: counts.all },
                { id: 'friends', label: 'اعضای قبلی', count: counts.friends },
                { id: 'frequent', label: 'پرتکرار', count: counts.frequent },
              ].map((item) => (
                <button key={item.id} type="button" onClick={() => onFilterChange(item.id as ContactFilter)} className={cn('inline-flex h-9 items-center gap-2 rounded-full border px-4 text-xs font-semibold transition', filter === item.id ? 'border-emerald-500 bg-emerald-50 text-emerald-700' : 'border-border bg-white text-slate-600 hover:border-emerald-300')}>
                  {item.label}
                  <span>{item.count.toLocaleString('fa-IR')}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="mb-5 rounded-[20px] border border-emerald-100 bg-emerald-50/40 p-4">
            <label className="mb-2 block text-sm font-semibold text-text">افزودن شماره موبایل</label>
            <div className="flex gap-2">
              <button type="button" onClick={onAddManualPhone} className="inline-flex h-11 shrink-0 items-center justify-center rounded-[14px] bg-emerald-600 px-4 text-sm font-semibold text-white transition hover:bg-emerald-700">افزودن</button>
              <input dir="ltr" value={manualPhone} onChange={(event) => onManualPhoneChange(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') onAddManualPhone(); }} placeholder="0912..." className="h-11 min-w-0 flex-1 rounded-[14px] border border-border bg-white px-4 text-left text-sm text-text outline-none transition focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10" />
            </div>
            <p className="mt-3 text-xs leading-6 text-slate-500">
              این شماره‌ها فعلاً عضو واقعی گروه نمی‌شوند. بعد از ساخت گروه، لینک دعوت را از صفحه جزئیات بساز و برای آن‌ها بفرست.
            </p>
          </div>

          {contactsLoading ? (
            <div className="rounded-[20px] border border-border bg-slate-50 p-8 text-center text-sm text-muted">در حال دریافت اعضای واقعی...</div>
          ) : null}

          {!contactsLoading && contactsList.length === 0 ? (
            <div className="rounded-[20px] border border-dashed border-border p-8 text-center text-sm leading-7 text-muted">
              هنوز مخاطب واقعی از گروه‌های قبلی پیدا نشد. می‌توانی شماره را دستی وارد کنی یا بعد از ساخت گروه لینک دعوت بسازی.
            </div>
          ) : null}

          <div className="grid gap-3 md:grid-cols-2">
            {filteredContacts.map((contact) => {
              const selected = selectedIds.includes(contact.id);
              return (
                <button key={contact.id} type="button" onClick={() => onToggleMember(contact.id)} className={cn('flex items-center justify-between rounded-[18px] border px-4 py-3 text-right transition', selected ? 'border-emerald-500 bg-emerald-50/70' : 'border-border bg-white hover:border-emerald-200 hover:bg-emerald-50/30')}>
                  <div className="flex min-w-0 items-center gap-3">
                    <Avatar label={contact.avatar} className={contact.avatarClass} />
                    <div className="min-w-0"><div className="truncate text-base font-semibold text-text">{contact.name}</div><div className="text-xs text-muted">{contact.phone}</div></div>
                  </div>
                  <div className={cn('flex h-7 w-7 shrink-0 items-center justify-center rounded-full border', selected ? 'border-emerald-500 bg-emerald-500 text-white' : 'border-border text-transparent')}>
                    <Check className="h-4 w-4" />
                  </div>
                </button>
              );
            })}
          </div>

          <div className="mt-4 flex items-center gap-2 text-sm font-semibold text-slate-600">
            <UserPlus className="h-4.5 w-4.5 text-slate-400" />
            {selectedMembers.length + manualPhones.length} نفر برای دعوت بعدی انتخاب شده‌اند
          </div>
        </div>
      </div>
    </div>
  );
}

export function CreateGroupWizard({ onBack, onComplete }: CreateGroupWizardProps) {
  const [currentStep, setCurrentStep] = useState<WizardStep>(1);
  const [direction, setDirection] = useState<1 | -1>(1);
  const [values, setValues] = useState<GroupInfoValues>({ name: '', groupType: '', description: '' });
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [contactsLoading, setContactsLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [manualPhone, setManualPhone] = useState('');
  const [manualPhones, setManualPhones] = useState<string[]>([]);
  const [filter, setFilter] = useState<ContactFilter>('all');
  const [searchValue, setSearchValue] = useState('');

  useEffect(() => {
    let ignore = false;

    async function loadRealContacts() {
      try {
        setContactsLoading(true);
        const [groups, currentUser] = await Promise.all([getMyGroups(), getCurrentUser().catch(() => null)]);
        const currentUserPhone = normalizePhone(currentUser?.phone_number || currentUser?.phone || currentUser?.username);
        const memberLists = await Promise.all(groups.slice(0, 8).map((group) => getGroupMembers(group.id).catch(() => [])));
        const byPhone = new Map<string, Contact>();

        memberLists.flat().forEach((member, index) => {
          const phone = normalizePhone(getMemberPhone(member));
          if (!phone || phone === currentUserPhone) return;
          if (byPhone.has(phone)) return;
          byPhone.set(phone, makeContactFromMember(member, index));
        });

        if (!ignore) setContacts(Array.from(byPhone.values()));
      } finally {
        if (!ignore) setContactsLoading(false);
      }
    }

    loadRealContacts();

    return () => {
      ignore = true;
    };
  }, []);

  const selectedMembers = useMemo(() => contacts.filter((contact) => selectedIds.includes(contact.id)), [contacts, selectedIds]);

  const updateField = <K extends keyof GroupInfoValues>(field: K, value: GroupInfoValues[K]) => {
    setValues((prev) => ({ ...prev, [field]: value }));
  };

  const goToStep = (nextStep: WizardStep) => {
    if (nextStep === currentStep) return;
    setDirection(nextStep > currentStep ? 1 : -1);
    setCurrentStep(nextStep);
  };

  const handleToggleMember = (id: string) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]));
  };

  const handleAddManualPhone = () => {
    const phone = normalizePhone(manualPhone);
    if (!phone || manualPhones.includes(phone)) return;
    setManualPhones((prev) => [...prev, phone]);
    setManualPhone('');
  };

  const handleFinish = () => {
    onComplete({
      name: values.name || 'گروه جدید',
      description: values.description,
      groupType: values.groupType,
      memberCount: selectedIds.length + manualPhones.length,
      selectedPhones: [...selectedMembers.map((member) => normalizePhone(member.phone)), ...manualPhones].filter(Boolean),
    });
  };

  return (
    <main className="px-4 py-6 sm:px-6 xl:px-8">
      <div className="mx-auto grid max-w-[1280px] gap-6 xl:grid-cols-[minmax(0,1fr)_280px]">
        <section className="card-surface order-1 overflow-hidden">
          <div className="border-b border-border/80 px-5 py-6 sm:px-8">
            <div className="flex items-center justify-between gap-4">
              <h1 className="text-[32px] font-extrabold tracking-[-0.03em] text-text">تشکیل گروه جدید</h1>
              <button type="button" onClick={onBack} className="inline-flex items-center gap-2 text-slate-600 transition hover:text-text"><ArrowLeft className="h-5 w-5" /><span className="text-sm font-semibold">بازگشت</span></button>
            </div>
            <div className="mt-8"><CreateGroupStepper currentStep={currentStep} steps={steps} /></div>
          </div>

          <div className="p-5 sm:p-8">
            <div key={currentStep} className={cn('will-change-transform', direction === 1 ? 'wizard-step-enter-forward' : 'wizard-step-enter-backward')}>
              {currentStep === 1 ? (
                <GroupInfoStep values={values} onChange={updateField} />
              ) : (
                <AddMembersStep contactsList={contacts} contactsLoading={contactsLoading} searchValue={searchValue} filter={filter} selectedIds={selectedIds} manualPhone={manualPhone} manualPhones={manualPhones} onSearchChange={setSearchValue} onFilterChange={setFilter} onToggleMember={handleToggleMember} onRemoveMember={handleToggleMember} onManualPhoneChange={setManualPhone} onAddManualPhone={handleAddManualPhone} onRemoveManualPhone={(phone) => setManualPhones((prev) => prev.filter((item) => item !== phone))} />
              )}
            </div>
          </div>

          <div className="border-t border-border/80 px-5 py-5 sm:px-8">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <div className="flex flex-col gap-3 sm:flex-row">
                {currentStep > 1 ? <button type="button" onClick={() => goToStep(1)} className="inline-flex h-12 items-center justify-center rounded-[16px] border border-border bg-white px-6 text-sm font-semibold text-slate-700 transition hover:bg-slate-50">مرحله قبل</button> : null}
                {currentStep < 2 ? (
                  <button type="button" onClick={() => goToStep(2)} className="inline-flex h-12 items-center justify-center gap-2 rounded-[16px] bg-gradient-to-l from-[#00915F] to-[#00A86B] px-6 text-sm font-semibold text-white shadow-[0_12px_28px_rgba(0,168,107,0.22)] transition hover:-translate-y-0.5">مرحله بعدی<ChevronLeft className="h-4.5 w-4.5" /></button>
                ) : (
                  <button type="button" onClick={handleFinish} className="inline-flex h-12 items-center justify-center gap-2 rounded-[16px] bg-gradient-to-l from-[#00915F] to-[#00A86B] px-6 text-sm font-semibold text-white shadow-[0_12px_28px_rgba(0,168,107,0.22)] transition hover:-translate-y-0.5">اتمام و ایجاد گروه<Check className="h-4.5 w-4.5" /></button>
                )}
              </div>
              <button type="button" onClick={onBack} className="inline-flex h-12 items-center justify-center rounded-[16px] border border-border bg-white px-6 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 sm:mr-auto">انصراف</button>
            </div>
          </div>
        </section>

        <SummaryCard values={values} memberCount={selectedIds.length + manualPhones.length} />
      </div>
    </main>
  );
}
