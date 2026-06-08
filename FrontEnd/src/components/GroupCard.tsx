import { useState } from 'react';
import {
  Archive,
  ChevronLeft,
  Eye,
  MoreVertical,
  Trash2,
  X,
} from 'lucide-react';
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

interface GroupCardProps {
  group: Group;
  onOpen?: (group: Group) => void;
  onDelete?: (group: Group) => void;
}

export function GroupCard({ group, onOpen, onDelete }: GroupCardProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const archived = group.status === 'ARCHIVED';

  const handleOpen = () => {
    setMenuOpen(false);
    onOpen?.(group);
  };

  const handleDelete = () => {
    setMenuOpen(false);
    onDelete?.(group);
  };

  return (
    <Card
      className={[
        'relative flex min-h-[196px] cursor-pointer flex-col overflow-visible p-6 transition hover:-translate-y-1 hover:shadow-[0_18px_50px_rgba(15,23,42,0.08)]',
        archived ? 'border-amber-100 bg-amber-50/35' : '',
      ].join(' ')}
      dir="rtl"
      role="button"
      tabIndex={0}
      onClick={handleOpen}
      onKeyDown={(event) => {
        if (event.key === 'Enter') {
          handleOpen();
        }
      }}
    >
      <div className="absolute left-4 top-4 z-20">
        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            setMenuOpen((prev) => !prev);
          }}
          className="flex h-9 w-9 items-center justify-center rounded-2xl text-slate-500 transition hover:bg-slate-100 hover:text-slate-800"
          aria-label="گزینه‌های گروه"
        >
          {menuOpen ? <X className="h-5 w-5" /> : <MoreVertical className="h-5 w-5" />}
        </button>

        {menuOpen ? (
          <div
            onClick={(event) => event.stopPropagation()}
            className="absolute left-0 top-11 z-30 w-[210px] overflow-hidden rounded-3xl border border-border bg-white p-2 text-right shadow-[0_18px_55px_rgba(15,23,42,0.16)]"
          >
            <button
              type="button"
              onClick={handleOpen}
              className="flex h-11 w-full items-center justify-between rounded-2xl px-3 text-sm font-bold text-slate-700 transition hover:bg-slate-50"
            >
              مشاهده جزئیات
              <Eye className="h-4 w-4" />
            </button>

            {!archived ? (
              <button
                type="button"
                onClick={handleDelete}
                className="mt-1 flex h-11 w-full items-center justify-between rounded-2xl px-3 text-sm font-bold text-rose-600 transition hover:bg-rose-50"
              >
                حذف از لیست
                <Trash2 className="h-4 w-4" />
              </button>
            ) : (
              <div className="mt-1 flex h-11 w-full items-center justify-between rounded-2xl bg-amber-50 px-3 text-sm font-bold text-amber-700">
                در آرشیو است
                <Archive className="h-4 w-4" />
              </div>
            )}
          </div>
        ) : null}
      </div>

      {archived ? (
        <div className="absolute right-4 top-4 inline-flex items-center gap-1.5 rounded-full bg-amber-100 px-2.5 py-1 text-[11px] font-bold text-amber-700">
          <Archive className="h-3.5 w-3.5" />
          آرشیو
        </div>
      ) : null}

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
