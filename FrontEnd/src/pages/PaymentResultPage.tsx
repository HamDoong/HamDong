import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { CheckCircle2, Loader2, WalletCards, XCircle } from 'lucide-react';
import {
  clearPendingWalletPayment,
  getPendingWalletPayment,
  paySettlementItemWithWallet,
  verifyPaymentIntent,
  type PaymentProvider,
} from '../lib/walletApi';
import { getFriendlyApiErrorMessage } from '../lib/userMessages';
import { MoneyWithWords } from '../lib/money';

function getProviderReference(params: URLSearchParams) {
  return (
    params.get('provider_reference') ||
    params.get('Authority') ||
    params.get('authority') ||
    params.get('ref') ||
    params.get('reference') ||
    undefined
  );
}

export function PaymentResultPage() {
  const location = useLocation();
  const params = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const [status, setStatus] = useState<'loading' | 'success' | 'failed'>('loading');
  const [title, setTitle] = useState('در حال بررسی پرداخت');
  const [description, setDescription] = useState('چند لحظه صبر کن تا نتیجه پرداخت بررسی شود.');
  const [amountMinor, setAmountMinor] = useState(0);

  useEffect(() => {
    let mounted = true;

    async function verifyPayment() {
      const pending = getPendingWalletPayment();
      const paymentIntentId = params.get('payment_intent_id') || params.get('intent_id') || pending?.paymentIntentId;
      const provider = (params.get('provider') || pending?.provider || 'FAKE').toUpperCase() as PaymentProvider;
      const providerReference = getProviderReference(params) || pending?.paymentIntentId;

      if (!paymentIntentId) {
        if (!mounted) return;
        setStatus('failed');
        setTitle('پرداختی برای بررسی پیدا نشد');
        setDescription('اطلاعات پرداخت در این صفحه پیدا نشد. از صفحه کیف پول دوباره پرداخت را شروع کن.');
        return;
      }

      try {
        const result = await verifyPaymentIntent({
          provider,
          paymentIntentId,
          providerReference,
        });

        if (!mounted) return;
        setAmountMinor(result.amount_minor || pending?.amountMinor || 0);

        if (String(result.status).toUpperCase() !== 'SUCCEEDED') {
          setStatus('failed');
          setTitle('پرداخت تأیید نشد');
          setDescription(result.failure_reason || 'پرداخت توسط درگاه تأیید نشد. اگر مبلغ از حسابت کم شده، وضعیت کیف پول را چند دقیقه دیگر بررسی کن.');
          return;
        }

        if (pending?.settlementPlanItemId) {
          await paySettlementItemWithWallet(
            pending.settlementPlanItemId,
            pending.walletPayIdempotencyKey,
          );
        }

        clearPendingWalletPayment();
        setStatus('success');
        setTitle(pending?.settlementPlanItemId ? 'پرداخت و تسویه انجام شد' : 'کیف پول شارژ شد');
        setDescription(
          pending?.settlementPlanItemId
            ? 'پرداخت در کیف پول ثبت شد و تسویه انتخاب‌شده هم انجام شد.'
            : 'مبلغ پرداختی به کیف پولت اضافه شد.',
        );
      } catch (error) {
        if (!mounted) return;
        setStatus('failed');
        setTitle('نتیجه پرداخت بررسی نشد');
        setDescription(getFriendlyApiErrorMessage(error, { defaultMessage: 'ارتباط با سرویس پرداخت برقرار نشد. چند لحظه بعد دوباره امتحان کن.' }));
      }
    }

    void verifyPayment();

    return () => {
      mounted = false;
    };
  }, [params]);

  const isLoading = status === 'loading';
  const isSuccess = status === 'success';

  return (
    <main dir="rtl" className="app-page flex min-h-screen items-center justify-center text-right text-text">
      <section className="w-full max-w-[520px] rounded-[28px] border border-emerald-100 bg-white p-6 shadow-[0_24px_70px_rgba(15,23,42,0.10)] dark:border-emerald-500/20 dark:bg-slate-900">
        <div className={[
          'mx-auto flex h-20 w-20 items-center justify-center rounded-full',
          isLoading
            ? 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-300'
            : isSuccess
              ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-200'
              : 'bg-rose-50 text-rose-600 dark:bg-rose-500/10 dark:text-rose-200',
        ].join(' ')}>
          {isLoading ? <Loader2 className="h-10 w-10 animate-spin" /> : isSuccess ? <CheckCircle2 className="h-10 w-10" /> : <XCircle className="h-10 w-10" />}
        </div>

        <div className="mt-5 text-center">
          <h1 className="text-xl font-black">{title}</h1>
          <p className="mt-3 text-sm font-semibold leading-7 text-muted dark:text-slate-400">{description}</p>
        </div>

        {amountMinor > 0 ? (
          <div className="mt-5 rounded-[22px] border border-emerald-100 bg-emerald-50/70 p-4 text-center dark:border-emerald-500/20 dark:bg-emerald-500/10">
            <div className="mb-2 flex items-center justify-center gap-2 text-sm font-black text-emerald-700 dark:text-emerald-200">
              <WalletCards className="h-4 w-4" />
              مبلغ پرداخت
            </div>
            <MoneyWithWords amount={amountMinor} valueClassName="text-2xl font-black text-emerald-700 dark:text-emerald-200" textClassName="mt-1 text-xs font-semibold text-emerald-700/70 dark:text-emerald-200/70" />
          </div>
        ) : null}

        <div className="mt-6 grid gap-2 sm:grid-cols-2">
          <Link to="/Dashboard#wallet" className="inline-flex min-h-12 items-center justify-center rounded-[18px] bg-emerald-600 px-4 text-sm font-black text-white transition hover:bg-emerald-700 dark:bg-emerald-500 dark:hover:bg-emerald-400">
            رفتن به کیف پول
          </Link>
          <Link to="/Dashboard#groups" className="inline-flex min-h-12 items-center justify-center rounded-[18px] border border-emerald-200 bg-white px-4 text-sm font-black text-emerald-700 transition hover:bg-emerald-50 dark:border-emerald-500/25 dark:bg-slate-950 dark:text-emerald-200 dark:hover:bg-emerald-500/10">
            مشاهده گروه‌ها
          </Link>
        </div>
      </section>
    </main>
  );
}
