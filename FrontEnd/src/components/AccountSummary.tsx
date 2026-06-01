import { Wallet } from 'lucide-react';
import { accountSummary } from '../data/mockData';
import { Card } from './ui/Card';

function AmountText({
  amount,
  tone,
}: {
  amount: string;
  tone: 'positive' | 'negative';
}) {
  return (
    <span className={`text-base font-bold ${tone === 'positive' ? 'text-emerald-600' : 'text-rose-500'}`}>
      {amount}
    </span>
  );
}

export function AccountSummary() {
  return (
    <Card variant="panel" className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <h3 className="text-[24px] font-bold leading-tight text-text">خلاصه حساب شما</h3>
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600">
          <Wallet className="h-5 w-5" strokeWidth={1.8} />
        </div>
      </div>

      <div className="space-y-5">
        {accountSummary.map((item) => (
          <div key={item.id} className="flex items-center justify-between gap-4">
            <span className="text-[15px] text-muted">{item.label}</span>
            <AmountText amount={item.amount} tone={item.tone} />
          </div>
        ))}
      </div>
    </Card>
  );
}
