import { ChevronLeft, MoreVertical } from 'lucide-react';
import type { Group } from '../types';
import { Card } from './ui/Card';

function GroupIllustration({ type }: { type: Group['illustration'] }) {
  if (type === 'trip') {
    return (
      <div className="relative h-[82px] w-[82px] overflow-hidden rounded-full border border-border bg-sky-50 shadow-inner">
        <div className="absolute inset-x-0 top-0 h-[58%] bg-gradient-to-b from-sky-100 via-sky-100 to-sky-50" />
        <div className="absolute inset-x-0 bottom-0 h-[34%] bg-gradient-to-r from-[#F4D9A5] via-[#F2CF8F] to-[#F7DFC0]" />
        <div className="absolute bottom-2 left-3 text-[24px]">🌴</div>
        <div className="absolute bottom-3 right-2 text-[24px]">🚐</div>
        <div className="absolute right-2 top-2 text-[18px]">☁️</div>
      </div>
    );
  }

  if (type === 'home') {
    return (
      <div className="relative h-[82px] w-[82px] overflow-hidden rounded-full border border-border bg-orange-50 shadow-inner">
        <div className="absolute inset-x-0 bottom-0 h-[28%] bg-gradient-to-r from-lime-300 to-emerald-400" />
        <div className="absolute bottom-3 left-1/2 -translate-x-1/2 text-[31px]">🏢</div>
        <div className="absolute right-2 top-2 text-[18px]">☀️</div>
      </div>
    );
  }

  return (
    <div className="relative h-[82px] w-[82px] overflow-hidden rounded-full border border-border bg-orange-50 shadow-inner">
      <div className="absolute inset-x-0 bottom-0 h-[24%] bg-[#E7C7A4]" />
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-[45%] text-[32px]">☕</div>
      <div className="absolute right-4 top-4 text-[15px]">✨</div>
    </div>
  );
}

function AmountText({ amount, tone }: { amount: string; tone: Group['tone'] }) {
  return (
    <span
      className={[
        'text-[20px] font-bold tracking-[-0.02em]',
        tone === 'positive' ? 'text-emerald-600' : 'text-rose-500',
      ].join(' ')}
    >
      {amount}
    </span>
  );
}

export function GroupCard({ group }: { group: Group }) {
  return (
    <Card className="relative flex min-h-[196px] flex-col overflow-hidden p-6" dir="rtl">
      <button
        type="button"
        className="absolute left-4 top-4 text-slate-500 transition hover:text-slate-800"
      >
        <MoreVertical className="h-5 w-5" />
      </button>

      <div className="mb-6 flex items-start gap-4">
        <div className="min-w-0 flex-1 text-right">
          <h3 className="text-[20px] font-bold leading-8 text-text">{group.name}</h3>
          <p className="mt-1 text-sm text-muted">{group.membersLabel}</p>
        </div>

        <GroupIllustration type={group.illustration} />
      </div>

      <div className="flex items-center justify-between text-sm text-muted">
        <span>{group.statusLabel}</span>
        <ChevronLeft className="h-4 w-4 text-slate-500" />
      </div>

      <div className="mt-auto pt-6 text-center">
        <AmountText amount={group.amount} tone={group.tone} />
      </div>
    </Card>
  );
}
