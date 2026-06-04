import { create } from 'zustand';
import type { SpeakerRole } from '@/types/domain';

export type SessionLifecycle = 'idle' | 'starting' | 'live' | 'stopping' | 'stopped';

export interface TranscriptEntry {
  id: string;
  speakerId: string;
  text: string;
  isFinal: boolean;
  atMs: number;
}

export interface ActiveSpeaker {
  id: string;
  label: string;
  role: SpeakerRole;
  isSpeaking: boolean;
  lastSpokeAtMs: number;
}

export interface CurrentCase {
  caseNumber: string;
  title: string;
  judge: string;
}

interface SessionState {
  lifecycle: SessionLifecycle;
  startedAt: number | null;
  elapsedSec: number;
  currentCase: CurrentCase | null;

  transcript: TranscriptEntry[];
  /** speakerId -> id of the currently-open partial entry */
  partialIndex: Record<string, string>;
  speakers: ActiveSpeaker[];

  audioLevel: number; // 0-100
  isMuted: boolean;

  // Actions
  start: (caseInfo: CurrentCase) => void;
  stop: () => void;
  reset: () => void;
  tick: () => void;

  upsertPartial: (speakerId: string, text: string, atMs: number) => void;
  commitFinalFor: (speakerId: string) => void;
  registerSpeaker: (id: string, label: string, role: SpeakerRole) => void;
  setSpeakerSpeaking: (id: string, speaking: boolean) => void;
  setAudioLevel: (level: number) => void;
  setMuted: (muted: boolean) => void;
  goLive: () => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  lifecycle: 'idle',
  startedAt: null,
  elapsedSec: 0,
  currentCase: null,
  transcript: [],
  partialIndex: {},
  speakers: [],
  audioLevel: 0,
  isMuted: false,

  start: (caseInfo) =>
    set({
      lifecycle: 'starting',
      currentCase: caseInfo,
      startedAt: null,
      elapsedSec: 0,
      transcript: [],
      partialIndex: {},
      speakers: [],
      audioLevel: 0,
    }),

  stop: () => set({ lifecycle: 'stopping', audioLevel: 0 }),

  reset: () =>
    set({
      lifecycle: 'idle',
      startedAt: null,
      elapsedSec: 0,
      currentCase: null,
      transcript: [],
      partialIndex: {},
      speakers: [],
      audioLevel: 0,
      isMuted: false,
    }),

  tick: () =>
    set((s) =>
      s.lifecycle === 'live' && s.startedAt != null
        ? { elapsedSec: Math.floor((Date.now() - s.startedAt) / 1000) }
        : s,
    ),

  goLive: () => set({ lifecycle: 'live', startedAt: Date.now() }),

  upsertPartial: (speakerId, text, atMs) =>
    set((s) => {
      const speakers = ensureSpeaker(s.speakers, speakerId);
      const speakersUpdated = speakers.map((sp) =>
        sp.id === speakerId ? { ...sp, isSpeaking: true, lastSpokeAtMs: atMs } : sp,
      );

      const existingId = s.partialIndex[speakerId];
      if (existingId) {
        return {
          transcript: s.transcript.map((e) =>
            e.id === existingId ? { ...e, text, atMs } : e,
          ),
          speakers: speakersUpdated,
        };
      }

      const id = `t-${atMs}-${speakerId}-${Math.random().toString(36).slice(2, 7)}`;
      return {
        transcript: [
          ...s.transcript,
          { id, speakerId, text, isFinal: false, atMs },
        ],
        partialIndex: { ...s.partialIndex, [speakerId]: id },
        speakers: speakersUpdated,
      };
    }),

  commitFinalFor: (speakerId) =>
    set((s) => {
      const id = s.partialIndex[speakerId];
      if (!id) return s;
      const next = { ...s.partialIndex };
      delete next[speakerId];
      return {
        transcript: s.transcript.map((e) => (e.id === id ? { ...e, isFinal: true } : e)),
        partialIndex: next,
        speakers: s.speakers.map((sp) =>
          sp.id === speakerId ? { ...sp, isSpeaking: false } : sp,
        ),
      };
    }),

  registerSpeaker: (id, label, role) =>
    set((s) => {
      const existing = s.speakers.find((sp) => sp.id === id);
      if (existing) {
        if (existing.role !== 'unknown') return s;
        return {
          speakers: s.speakers.map((sp) =>
            sp.id === id ? { ...sp, label, role } : sp,
          ),
        };
      }
      return {
        speakers: [
          ...s.speakers,
          { id, label, role, isSpeaking: false, lastSpokeAtMs: 0 },
        ],
      };
    }),

  setSpeakerSpeaking: (id, speaking) =>
    set((s) => ({
      speakers: s.speakers.map((sp) => (sp.id === id ? { ...sp, isSpeaking: speaking } : sp)),
    })),

  setAudioLevel: (level) => set({ audioLevel: level }),
  setMuted: (muted) => set({ isMuted: muted }),
}));

function ensureSpeaker(speakers: ActiveSpeaker[], id: string): ActiveSpeaker[] {
  if (speakers.some((s) => s.id === id)) return speakers;
  return [
    ...speakers,
    { id, label: id, role: 'unknown', isSpeaking: false, lastSpokeAtMs: 0 },
  ];
}
