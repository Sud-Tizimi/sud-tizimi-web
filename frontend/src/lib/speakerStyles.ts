import type { SpeakerRole } from '@/types/domain';

interface RoleStyle {
  /** Pill / chip background */
  bg: string;
  /** Primary text */
  text: string;
  /** Strong accent (dot, left bar) */
  accent: string;
  /** Soft border */
  border: string;
  /** Hover background for rows */
  hover: string;
}

export const ROLE_STYLES: Record<SpeakerRole | 'unknown', RoleStyle> = {
  judge: {
    bg: 'bg-primary-50',
    text: 'text-primary-700',
    accent: 'bg-primary-500',
    border: 'border-primary-200',
    hover: 'hover:bg-primary-50/60',
  },
  plaintiff: {
    bg: 'bg-amber-50',
    text: 'text-amber-700',
    accent: 'bg-amber-500',
    border: 'border-amber-200',
    hover: 'hover:bg-amber-50/60',
  },
  defendant: {
    bg: 'bg-rose-50',
    text: 'text-rose-700',
    accent: 'bg-rose-500',
    border: 'border-rose-200',
    hover: 'hover:bg-rose-50/60',
  },
  witness: {
    bg: 'bg-sky-50',
    text: 'text-sky-700',
    accent: 'bg-sky-500',
    border: 'border-sky-200',
    hover: 'hover:bg-sky-50/60',
  },
  lawyer: {
    bg: 'bg-violet-50',
    text: 'text-violet-700',
    accent: 'bg-violet-500',
    border: 'border-violet-200',
    hover: 'hover:bg-violet-50/60',
  },
  unknown: {
    bg: 'bg-surface-container',
    text: 'text-ink-muted',
    accent: 'bg-ink-muted',
    border: 'border-outline-soft',
    hover: 'hover:bg-surface-container-high',
  },
};

export const ROLE_LABEL: Record<SpeakerRole | 'unknown', string> = {
  judge: 'Judge',
  plaintiff: 'Plaintiff',
  defendant: 'Defendant',
  witness: 'Witness',
  lawyer: 'Lawyer',
  unknown: 'Unknown',
};
