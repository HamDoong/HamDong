import type { HTMLAttributes, ReactNode } from 'react';

type CardVariant = 'default' | 'panel' | 'tint';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: CardVariant;
  children: ReactNode;
}

const variantClasses: Record<CardVariant, string> = {
  default: 'rounded-3xl border border-border bg-white shadow-soft',
  panel: 'rounded-[22px] border border-border bg-white shadow-panel',
  tint: 'rounded-3xl border border-emerald-100 bg-panel-tint shadow-soft',
};

export function Card({
  variant = 'default',
  children,
  className = '',
  ...props
}: CardProps) {
  return (
    <div className={`${variantClasses[variant]} ${className}`.trim()} {...props}>
      {children}
    </div>
  );
}
