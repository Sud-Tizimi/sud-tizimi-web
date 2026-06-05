import type { CaseStatus } from '@/types/domain';

/**
 * Map a workflow case status to a Badge variant + a CSS dot color
 * (for the inline status pill in the table).
 */
export const CASE_STATUS_BADGE: Record<
  CaseStatus,
  { variant: 'success' | 'warning' | 'error' | 'info' | 'neutral'; dot: string }
> = {
  draft: { variant: 'neutral', dot: 'bg-outline' },
  uploaded: { variant: 'info', dot: 'bg-primary-500' },
  under_review: { variant: 'warning', dot: 'bg-amber-500' },
  approved: { variant: 'success', dot: 'bg-emerald-500' },
  returned: { variant: 'error', dot: 'bg-error' },
};
