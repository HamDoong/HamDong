import { recentActivities } from '../data/mockData';
import { Card } from './ui/Card';

export function RecentActivities() {
  return (
    <Card variant="panel" className="p-6">
      <div className="mb-5 flex items-center justify-between">
        <h3 className="text-[24px] font-bold leading-tight text-text">فعالیت‌های اخیر</h3>
        <button type="button" className="text-[15px] font-semibold text-emerald-600">
          مشاهده همه
        </button>
      </div>

      <div className="space-y-2">
        {recentActivities.map((activity, index) => {
          const Icon = activity.icon;

          return (
            <div key={activity.id}>
              <div className="flex items-start gap-4 py-3">
                <div
                  className={`mt-0.5 flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl ${activity.iconBoxClassName}`}
                >
                  <Icon className={`h-5 w-5 ${activity.iconClassName}`} strokeWidth={1.9} />
                </div>

                <div className="min-w-0 text-right">
                  <div className="text-[15px] font-semibold leading-7 text-slate-800">
                    {activity.title}
                  </div>
                  <div className="mt-1 text-[14px] text-muted">{activity.subtitle}</div>
                </div>
              </div>

              {index !== recentActivities.length - 1 ? <div className="h-px bg-slate-100" /> : null}
            </div>
          );
        })}
      </div>
    </Card>
  );
}
