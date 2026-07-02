import type { HTMLAttributes, ReactNode } from 'react';

type CardVariant = 'default' | 'panel' | 'tint';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: CardVariant;
  children: ReactNode;
}

const variantClasses: Record<CardVariant, string> = {
  default: 'app-card rounded-3xl border border-border bg-surface shadow-soft',
  panel: 'app-panel rounded-[22px] border border-border bg-surface shadow-panel',
  tint: 'app-card app-card-tint rounded-3xl border border-primary/15 bg-panel-tint shadow-soft',
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
