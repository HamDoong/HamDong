import { Info, Users } from 'lucide-react';
import type { CreateGroupDraft, CreateGroupStep, GroupTypeOption } from '../../types';
import { Card } from '../ui/Card';

const groupTypeLabels: Record<GroupTypeOption, string> = {
  trip: 'سفر',
  food: 'غذا و رستوران',
  home: 'خانه و زندگی',
  other: 'سایر',
};

const stepMessages: Record<CreateGroupStep, string> = {
  1: 'بعد از ایجاد گروه می‌توانید اعضای خود را اضافه کرده و شروع به ثبت هزینه‌ها کنید.',
  2: 'پس از دعوت اعضا، می‌توانید هزینه‌ها را ثبت کرده و تسویه حساب را شروع کنید.',
  3: 'پس از ایجاد گروه، می‌توانید هزینه‌ها را ثبت کرده و تسویه حساب را شروع کنید.',
};

interface GroupSummaryCardProps {
  draft: CreateGroupDraft;
  step: CreateGroupStep;
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="space-y-2 text-right">
      <div className="text-[14px] text-muted">{label}</div>
      <div className="text-[18px] font-semibold text-text">{value}</div>
    </div>
  );
}

export function GroupSummaryCard({ draft, step }: GroupSummaryCardProps) {
  const nameValue = draft.name.trim() || '-';
  const typeValue = draft.type ? groupTypeLabels[draft.type] : '-';
  const dateValue = draft.startDate.trim() || (step === 1 ? '-' : 'تعیین نشده');
  const membersValue = `${draft.selectedMemberIds.length || 0} نفر`;

  return (
    <Card variant="panel" className="h-full p-6">
      <div className="mb-8 flex items-center justify-between">
        <h2 className="text-[28px] font-bold leading-tight text-text">خلاصه گروه</h2>
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-50 text-primary">
          <Users className="h-5 w-5" strokeWidth={1.9} />
        </div>
      </div>

      <div className="space-y-8">
        <SummaryRow label="نام گروه" value={nameValue} />
        <SummaryRow label="نوع گروه" value={typeValue} />
        <SummaryRow label="تاریخ شروع" value={dateValue} />
        <SummaryRow label="تعداد اعضا" value={membersValue} />
      </div>

      <div className="mt-10 rounded-3xl border border-emerald-100 bg-emerald-50/50 p-4 text-right">
        <div className="mb-2 flex items-center justify-between">
          <Info className="h-5 w-5 text-primary" strokeWidth={1.9} />
        </div>
        <p className="text-[14px] leading-7 text-slate-600">{stepMessages[step]}</p>
      </div>
    </Card>
  );
}
