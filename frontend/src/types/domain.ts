export type SessionStatus = 'live' | 'completed' | 'paused';

export type SpeakerRole = 'judge' | 'plaintiff' | 'defendant' | 'witness' | 'lawyer' | 'unknown';

export interface SpeakerProfile {
  id: string;
  label: string;
  role: SpeakerRole;
  fullName?: string;
}
