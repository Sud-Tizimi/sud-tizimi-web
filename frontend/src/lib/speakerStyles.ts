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

export const ROLE_STYLES: Record<SpeakerRole, RoleStyle> = {
  speaker: {
    bg: 'bg-primary-50',
    text: 'text-primary-700',
    accent: 'bg-primary-500',
    border: 'border-primary-200',
    hover: 'hover:bg-primary-50/60',
  },
  unknown: {
    bg: 'bg-surface-container',
    text: 'text-ink-muted',
    accent: 'bg-ink-muted',
    border: 'border-outline-soft',
    hover: 'hover:bg-surface-container-high',
  },
};
