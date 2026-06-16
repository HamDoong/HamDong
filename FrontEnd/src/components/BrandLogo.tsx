const BRAND_LOGO_SRC = '/brand/hamdong-logo.svg';

function cn(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(' ');
}

export function LogoMark({ className = '' }: { className?: string }) {
  return (
    <img
      src={BRAND_LOGO_SRC}
      alt=""
      aria-hidden="true"
      className={cn('block h-10 w-10 shrink-0 object-contain', className)}
      draggable={false}
    />
  );
}

export function BrandLogo({
  className = '',
  markClassName = '',
  textClassName = '',
}: {
  className?: string;
  markClassName?: string;
  textClassName?: string;
}) {
  return (
    <span className={cn('flex min-w-0 items-center gap-2.5', className)}>
      <LogoMark className={markClassName} />
      <span className={cn('truncate font-black text-text', textClassName)}>همدنگ</span>
    </span>
  );
}
