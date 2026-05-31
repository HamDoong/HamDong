import {
  Check,
  Copy,
  Link2,
  MessageCircleMore,
  MoreHorizontal,
  Plus,
  Send,
  ShieldCheck,
  Smartphone,
  Users,
} from 'lucide-react';
import { useMemo, useState } from 'react';
import { createGroupContacts } from '../../data/mockData';
import type { CreateGroupDraft, GroupTypeOption } from '../../types';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';

const inviteLink = 'https://hamdong.app/invite/7k3a9b';

const groupTypeLabels: Record<GroupTypeOption, string> = {
  trip: 'سفر',
  food: 'غذا و رستوران',
  home: 'خانه و زندگی',
  other: 'سایر',
};

function ContactAvatarStack({ memberIds }: { memberIds: number[] }) {
  const contacts = createGroupContacts.filter((contact) => memberIds.includes(contact.id)).slice(0, 3);

  return (
    <div className="flex items-center justify-center">
      <div className="flex -space-x-2 space-x-reverse">
        {contacts.map((contact) => (
          <div
            key={contact.id}
            className={`flex h-10 w-10 items-center justify-center rounded-full border-2 border-white bg-gradient-to-br text-sm font-bold text-white shadow-sm ${contact.avatarGradient}`}
          >
            {contact.avatarInitial}
          </div>
        ))}
        <div className="flex h-10 w-10 items-center justify-center rounded-full border-2 border-white bg-slate-100 text-sm font-semibold text-slate-500 shadow-sm">
          +5
        </div>
      </div>
    </div>
  );
}

function InvitePreviewIllustration() {
  return (
    <div className="relative mx-auto h-[100px] w-[100px] overflow-hidden rounded-full border border-border bg-sky-50 shadow-inner">
      <div className="absolute inset-x-0 top-0 h-[58%] bg-gradient-to-b from-sky-100 via-sky-100 to-sky-50" />
      <div className="absolute inset-x-0 bottom-0 h-[34%] bg-gradient-to-r from-[#F4D9A5] via-[#F2CF8F] to-[#F7DFC0]" />
      <div className="absolute bottom-2 left-3 text-[28px]">🌴</div>
      <div className="absolute bottom-3 right-2 text-[28px]">🚐</div>
      <div className="absolute right-2 top-2 text-[18px]">☁️</div>
    </div>
  );
}

interface InviteStepProps {
  draft: CreateGroupDraft;
  onPrev: () => void;
  onComplete: () => void;
}

export function InviteStep({ draft, onPrev, onComplete }: InviteStepProps) {
  const [copied, setCopied] = useState(false);
  const [phoneInvite, setPhoneInvite] = useState('');

  const selectedCount = draft.selectedMemberIds.length || 3;
  const groupName = draft.name.trim() || 'سفر شمال تابستان ۱۴۰۳';
  const groupTypeLabel = draft.type ? groupTypeLabels[draft.type] : 'سفر';

  const shareItems = useMemo(
    () => [
      { key: 'copy', label: 'کپی لینک', icon: Link2 },
      { key: 'whatsapp', label: 'واتساپ', icon: MessageCircleMore },
      { key: 'telegram', label: 'تلگرام', icon: Send },
      { key: 'sms', label: 'پیامک', icon: Smartphone },
      { key: 'other', label: 'سایر', icon: MoreHorizontal },
    ],
    [],
  );

  const handleCopy = async () => {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(inviteLink);
      }
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card variant="default" className="p-5 sm:p-6">
        <div className="mb-6 text-center">
          <h2 className="text-[20px] font-bold text-text sm:text-[22px]">دعوت اعضا به گروه</h2>
          <p className="mt-2 text-[14px] text-muted">
            لینک دعوت گروه خود را با دوستانتان به اشتراک بگذارید.
          </p>
        </div>

        <div className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)]">
          <Card variant="default" className="p-5">
            <div className="mb-4 text-right text-[15px] font-semibold text-text">پیش‌نمایش دعوت</div>
            <div className="space-y-4 text-center">
              <InvitePreviewIllustration />
              <div>
                <div className="text-[28px] font-bold leading-tight text-text">{groupName}</div>
                <div className="mt-2 text-[14px] text-muted">دعوت به گروه در همدنگ</div>
              </div>

              <ContactAvatarStack memberIds={draft.selectedMemberIds} />

              <div className="text-[16px] font-semibold text-slate-700">{Math.max(selectedCount, 3) + 9} عضو</div>

              <p className="mx-auto max-w-[240px] text-[14px] leading-7 text-slate-600">
                بیایید هزینه‌ها را با هم مدیریت کنیم و سفر خاطره‌انگیزی داشته باشیم! 🚐🌿
              </p>

              <div className="inline-flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1 text-sm font-semibold text-primary">
                <Users className="h-4 w-4" />
                {groupTypeLabel}
              </div>
            </div>
          </Card>

          <div className="space-y-5">
            <div className="text-right">
              <label className="mb-2 block text-sm font-semibold text-slate-700">لینک دعوت</label>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <Button
                  variant="secondary"
                  className="h-12 shrink-0 gap-2 border-emerald-200 bg-emerald-50 text-primary hover:bg-emerald-100"
                  onClick={handleCopy}
                >
                  {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                  {copied ? 'کپی شد' : 'کپی لینک'}
                </Button>

                <div className="relative flex-1">
                  <Link2 className="pointer-events-none absolute right-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
                  <input value={inviteLink} readOnly className="form-input pr-12 text-left" dir="ltr" />
                </div>
              </div>
            </div>

            <div className="rounded-3xl border border-emerald-100 bg-emerald-50/50 p-4 text-right">
              <div className="flex items-start justify-between gap-4">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-white/80 text-primary">
                  <ShieldCheck className="h-6 w-6" strokeWidth={1.9} />
                </div>

                <div className="flex-1">
                  <p className="text-[14px] leading-7 text-slate-600">
                    هر کسی که این لینک را داشته باشد می‌تواند به گروه بپیوندد.
                  </p>
                  <button type="button" className="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-primary">
                    <SettingsPlaceholder />
                    تغییر تنظیمات لینک
                  </button>
                </div>
              </div>
            </div>

            <div className="text-right">
              <div className="mb-3 text-[15px] font-semibold text-text">اشتراک گذاری سریع</div>
              <div className="grid gap-3 sm:grid-cols-5">
                {shareItems.map((item) => {
                  const Icon = item.icon;

                  return (
                    <button
                      key={item.key}
                      type="button"
                      className="flex h-20 flex-col items-center justify-center gap-2 rounded-2xl border border-border bg-white text-slate-700 transition hover:border-emerald-200 hover:bg-emerald-50/30"
                    >
                      <Icon className="h-5 w-5" />
                      <span className="text-sm font-medium">{item.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="h-px flex-1 bg-border" />
              <span className="text-sm text-muted">یا</span>
              <div className="h-px flex-1 bg-border" />
            </div>

            <div className="text-right">
              <label className="mb-2 block text-sm font-semibold text-slate-700">دعوت با شماره موبایل</label>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <Button
                  variant="secondary"
                  className="h-12 shrink-0 border-emerald-100 bg-emerald-50 text-primary hover:bg-emerald-100"
                >
                  <Plus className="h-4 w-4" />
                  افزودن
                </Button>
                <input
                  value={phoneInvite}
                  onChange={(event) => setPhoneInvite(event.target.value)}
                  placeholder="شماره موبایل را وارد کنید"
                  className="form-input flex-1"
                />
              </div>
            </div>
          </div>
        </div>
      </Card>

      <div className="flex flex-col gap-3 border-t border-border pt-6 sm:flex-row sm:items-center sm:justify-between">
        <Button variant="secondary" className="h-12 px-8 text-base font-semibold" onClick={onPrev}>
          مرحله قبل
        </Button>

        <Button className="h-12 px-8 text-base font-semibold" onClick={onComplete}>
          <Check className="h-5 w-5" />
          اتمام و ایجاد گروه
        </Button>
      </div>
    </div>
  );
}

function SettingsPlaceholder() {
  return <span className="inline-block h-2.5 w-2.5 rounded-full bg-primary" />;
}
