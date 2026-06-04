import type { ReactNode } from 'react';
import { Card } from './Card';
import { cn } from '@/lib/cn';

interface StatCardProps {
  label: string;
  value: ReactNode;
  delta?: { value: string; direction: 'up' | 'down' | 'flat' };
  icon?: ReactNode;
  hint?: string;
  className?: string;
}

export function StatCard({ label, value, delta, icon, hint, className }: StatCardProps) {
  return (
    <Card padding="md" className={cn('flex flex-col gap-3', className)}>
      <div className="flex items-center justify-between">
        <span className="text-mono text-ink-muted">{label}</span>
        {icon && (
          <span className="text-primary-500 h-9 w-9 rounded-md bg-primary-50 inline-flex items-center justify-center">
            {icon}
          </span>
        )}
      </div>

      <div className="flex items-baseline gap-3">
        <span className="text-headline-md text-ink tabular-nums">{value}</span>
        {delta && (
          <span
            className={cn(
              'text-body-md font-medium tabular-nums',
              delta.direction === 'up' && 'text-emerald-500',
              delta.direction === 'down' && 'text-error',
              delta.direction === 'flat' && 'text-ink-muted',
            )}
          >
            {delta.direction === 'up' ? '↑' : delta.direction === 'down' ? '↓' : '→'} {delta.value}
          </span>
        )}
      </div>

      {hint && <span className="text-caption text-ink-muted">{hint}</span>}
    </Card>
  );
}
