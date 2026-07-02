import type { HTMLAttributes, ReactNode } from 'react';
import { cn } from '@/lib/cn';

type BadgeVariant = 'success' | 'warning' | 'error' | 'info' | 'neutral' | 'live';

const VARIANT_STYLES: Record<BadgeVariant, string> = {
  success: 'bg-emerald-100 text-emerald-600 border-emerald-200',
  warning: 'bg-amber-50 text-amber-700 border-amber-200',
  error: 'bg-error-container text-error-onContainer border-red-200',
  info: 'bg-primary-50 text-primary-600 border-primary-100',
  neutral: 'bg-surface-container text-ink-muted border-outline-soft',
  live: 'bg-error-container text-error border-red-200',
};

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  dot?: boolean;
  children: ReactNode;
}

export function Badge({ variant = 'neutral', dot, className, children, ...rest }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex max-w-full items-center gap-1.5 px-2.5 py-1 min-h-6 rounded-full border text-label-md uppercase tracking-wide leading-tight whitespace-normal break-words text-left',
        VARIANT_STYLES[variant],
        className,
      )}
      {...rest}
    >
      {dot && (
        <span
          className={cn(
            'h-1.5 w-1.5 rounded-full',
            variant === 'live' && 'bg-error animate-pulse-dot',
            variant === 'success' && 'bg-emerald-300',
            variant === 'warning' && 'bg-amber-500',
            variant === 'error' && 'bg-error',
            variant === 'info' && 'bg-primary-500',
            variant === 'neutral' && 'bg-outline',
          )}
        />
      )}
      {children}
    </span>
  );
}
