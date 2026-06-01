import { Search, UserRound, Users, X } from 'lucide-react';
import { useMemo, useState } from 'react';
import { createGroupContacts } from '../../data/mockData';
import type { Contact, ContactCategory } from '../../types';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';

const filters: Array<{ key: 'all' | ContactCategory; label: string }> = [
  { key: 'all', label: 'همه' },
  { key: 'friends', label: 'دوستان' },
  { key: 'frequent', label: 'همیشگی' },
];

function ContactAvatar({
  contact,
  size = 'h-10 w-10',
}: {
  contact: Contact;
  size?: string;
}) {
  return (
    <div
      className={`flex ${size} shrink-0 items-center justify-center rounded-full bg-gradient-to-br text-sm font-bold text-white shadow-sm ${contact.avatarGradient}`}
    >
      {contact.avatarInitial}
    </div>
  );
}

interface AddMembersStepProps {
  selectedMemberIds: number[];
  onSelectedMemberIdsChange: (memberIds: number[]) => void;
  onCancel: () => void;
  onPrev: () => void;
  onNext: () => void;
}

export function AddMembersStep({
  selectedMemberIds,
  onSelectedMemberIdsChange,
  onCancel,
  onPrev,
  onNext,
}: AddMembersStepProps) {
  const [activeFilter, setActiveFilter] = useState<'all' | ContactCategory>('all');
  const [query, setQuery] = useState('');

  const counts = useMemo(
    () => ({
      all: createGroupContacts.length,
      friends: createGroupContacts.filter((contact) => contact.category === 'friends').length,
      frequent: createGroupContacts.filter((contact) => contact.category === 'frequent').length,
    }),
    [],
  );

  const filteredContacts = useMemo(() => {
    return createGroupContacts.filter((contact) => {
      const matchesFilter = activeFilter === 'all' || contact.category === activeFilter;
      const normalizedQuery = query.trim();
      const matchesQuery =
        normalizedQuery.length === 0 ||
        contact.name.includes(normalizedQuery) ||
        contact.phone.includes(normalizedQuery);

      return matchesFilter && matchesQuery;
    });
  }, [activeFilter, query]);

  const selectedContacts = createGroupContacts.filter((contact) =>
    selectedMemberIds.includes(contact.id),
  );

  const toggleContact = (contactId: number) => {
    if (selectedMemberIds.includes(contactId)) {
      onSelectedMemberIdsChange(selectedMemberIds.filter((id) => id !== contactId));
      return;
    }

    onSelectedMemberIdsChange([...selectedMemberIds, contactId]);
  };

  return (
    <div className="space-y-6">
      <Card variant="default" className="overflow-hidden">
        <div className="flex flex-col xl:flex-row">
          <section className="border-b border-border p-5 sm:p-6 xl:w-[36%] xl:border-b-0 xl:border-l">
            <div className="mb-6 flex items-center justify-between">
              <h2 className="text-[20px] font-bold text-text">اعضای انتخاب شده</h2>
              <div className="flex h-8 min-w-8 items-center justify-center rounded-full bg-emerald-50 px-2 text-sm font-bold text-primary">
                {selectedContacts.length}
              </div>
            </div>

            <div className="space-y-3">
              {selectedContacts.length > 0 ? (
                selectedContacts.map((contact) => (
                  <div
                    key={contact.id}
                    className="flex items-center justify-between rounded-2xl border border-border bg-white px-4 py-3"
                  >
                    <button
                      type="button"
                      onClick={() => toggleContact(contact.id)}
                      className="flex h-8 w-8 items-center justify-center rounded-full text-slate-500 transition hover:bg-slate-100 hover:text-slate-800"
                    >
                      <X className="h-4 w-4" strokeWidth={2.1} />
                    </button>

                    <div className="flex min-w-0 items-center gap-3">
                      <div className="min-w-0 text-right">
                        <div className="truncate text-[16px] font-semibold text-text">
                          {contact.name}
                          {contact.isSelf ? ' (شما)' : ''}
                        </div>
                      </div>
                      <ContactAvatar contact={contact} />
                    </div>
                  </div>
                ))
              ) : (
                <div className="rounded-2xl border border-dashed border-border bg-slate-50 px-4 py-8 text-center text-sm text-muted">
                  هنوز عضوی انتخاب نشده است.
                </div>
              )}
            </div>
          </section>

          <section className="min-w-0 flex-1 p-5 sm:p-6">
            <div className="mb-6 text-center">
              <h2 className="text-[20px] font-bold text-text">افزودن اعضا</h2>
              <p className="mt-2 text-[14px] text-muted">
                دوستان خود را برای اضافه شدن به گروه انتخاب کنید.
              </p>
            </div>

            <div className="relative">
              <Search className="pointer-events-none absolute right-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="جستجو با نام یا شماره موبایل..."
                className="form-input pr-12"
              />
            </div>

            <div className="mt-5 grid grid-cols-3 gap-2 rounded-2xl border border-border bg-slate-50/70 p-1">
              {filters.map((filter) => {
                const isActive = activeFilter === filter.key;

                return (
                  <button
                    key={filter.key}
                    type="button"
                    onClick={() => setActiveFilter(filter.key)}
                    className={[
                      'rounded-2xl px-3 py-2 text-sm font-semibold transition',
                      isActive ? 'bg-emerald-50 text-primary shadow-sm' : 'text-slate-600 hover:bg-white',
                    ].join(' ')}
                  >
                    {filter.label} ({counts[filter.key]})
                  </button>
                );
              })}
            </div>

            <div className="mt-4 overflow-hidden rounded-3xl border border-border">
              <div className="max-h-[340px] overflow-y-auto">
                {filteredContacts.map((contact, index) => {
                  const selected = selectedMemberIds.includes(contact.id);

                  return (
                    <button
                      key={contact.id}
                      type="button"
                      onClick={() => toggleContact(contact.id)}
                      className="flex w-full items-center justify-between gap-4 bg-white px-4 py-3 text-right transition hover:bg-slate-50"
                    >
                      <div className="shrink-0 text-[15px] text-muted">{contact.phone}</div>

                      <div className="flex min-w-0 items-center gap-3">
                        <div className="min-w-0 text-right">
                          <div className="truncate text-[16px] font-semibold text-text">{contact.name}</div>
                          {contact.isSelf ? (
                            <span className="mt-1 inline-flex items-center rounded-full bg-emerald-50 px-2 py-1 text-[12px] font-bold text-primary">
                              شما
                            </span>
                          ) : null}
                        </div>

                        <ContactAvatar contact={contact} />
                      </div>

                      <span
                        className={[
                          'flex h-6 w-6 shrink-0 items-center justify-center rounded-md border transition',
                          selected
                            ? 'border-primary bg-primary text-white'
                            : 'border-slate-300 bg-white text-transparent',
                        ].join(' ')}
                      >
                        ✓
                      </span>

                      {index !== filteredContacts.length - 1 ? (
                        <span className="sr-only">separator</span>
                      ) : null}
                    </button>
                  );
                })}
              </div>

              <div className="border-t border-border bg-slate-50/70 px-4 py-3">
                <div className="flex items-center gap-2 text-[15px] font-medium text-slate-700">
                  <Users className="h-4 w-4 text-muted" />
                  {selectedContacts.length} نفر انتخاب شده‌اند
                </div>
              </div>
            </div>
          </section>
        </div>
      </Card>

      <div className="flex flex-col gap-3 border-t border-border pt-6 sm:flex-row sm:items-center sm:justify-between">
        <Button variant="secondary" className="h-12 px-8 text-base font-semibold" onClick={onCancel}>
          انصراف
        </Button>

        <div className="flex flex-col gap-3 sm:flex-row">
          <Button variant="secondary" className="h-12 px-8 text-base font-semibold" onClick={onPrev}>
            مرحله قبل
          </Button>
          <Button className="h-12 px-8 text-base font-semibold" onClick={onNext}>
            مرحله بعدی
          </Button>
        </div>
      </div>
    </div>
  );
}
