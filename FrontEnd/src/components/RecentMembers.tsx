import { recentMembers } from '../data/mockData';
import { Card } from './ui/Card';

function Avatar({
  label,
  gradient,
}: {
  label: string;
  gradient: string;
}) {
  return (
    <div
      className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br text-sm font-bold text-white shadow-sm ${gradient}`}
    >
      {label}
    </div>
  );
}

function AmountText({
  amount,
  tone,
}: {
  amount: string;
  tone: 'positive' | 'negative';
}) {
  return (
    <span
      className={`shrink-0 text-[15px] font-bold ${
        tone === 'positive' ? 'text-emerald-600' : 'text-rose-500'
      }`}
    >
      {amount}
    </span>
  );
}

export function RecentMembers() {
  return (
    <Card variant="panel" className="p-6">
      <div className="mb-5 flex items-center justify-between">
        <h3 className="text-[24px] font-bold leading-tight text-text">اعضای اخیر</h3>
        <button type="button" className="text-[15px] font-semibold text-emerald-600">
          مشاهده همه
        </button>
      </div>

      <div className="space-y-1">
        {recentMembers.map((member, index) => (
          <div key={member.id}>
            <div className="flex items-center justify-between gap-4 py-3">
              <div className="flex min-w-0 items-center gap-3">
                <Avatar label={member.avatarInitial} gradient={member.avatarGradient} />

                <div className="min-w-0 text-right">
                  <div className="truncate text-[15px] font-medium text-slate-800">
                    {member.name}
                  </div>
                  {member.badge ? (
                    <div className="mt-1">
                      <span className="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-1 text-[12px] font-semibold text-emerald-700">
                        {member.badge}
                      </span>
                    </div>
                  ) : null}
                </div>
              </div>

              <AmountText amount={member.amount} tone={member.tone} />
            </div>

            {index !== recentMembers.length - 1 ? <div className="h-px bg-slate-100" /> : null}
          </div>
        ))}
      </div>
    </Card>
  );
}
