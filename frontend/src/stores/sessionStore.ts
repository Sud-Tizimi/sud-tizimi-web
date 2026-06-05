import { create } from 'zustand';
import type { SpeakerRole } from '@/types/domain';

export type SessionLifecycle = 'idle' | 'starting' | 'live' | 'stopping' | 'stopped';

export interface TranscriptEntry {
  id: string;
  speakerId: string;
  text: string;
  isFinal: boolean;
  atMs: number;
  startMs?: number;
  endMs?: number;
  confidence?: number;
}

export interface FinalTranscriptSegment {
  speakerId: string;
  speakerLabel: string;
  shortLabel: string;
  text: string;
  atMs: number;
  startMs?: number;
  endMs?: number;
  confidence?: number;
}

export interface ActiveSpeaker {
  id: string;
  label: string;
  shortLabel: string;
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
  replaceWithFinalSegments: (segments: FinalTranscriptSegment[]) => void;
  registerSpeaker: (id: string, label?: string, role?: SpeakerRole, shortLabel?: string) => void;
  setSpeakerSpeaking: (id: string, speaking: boolean) => void;
  setAudioLevel: (level: number) => void;
  setMuted: (muted: boolean) => void;
  goLive: () => void;
  finish: () => void;
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
  finish: () => set({ lifecycle: 'stopped', audioLevel: 0 }),

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

  replaceWithFinalSegments: (segments) =>
    set(() => {
      const speakers: ActiveSpeaker[] = [];
      const seen = new Set<string>();
      const transcript: TranscriptEntry[] = segments.map((seg, index) => {
        if (!seen.has(seg.speakerId)) {
          seen.add(seg.speakerId);
          speakers.push({
            id: seg.speakerId,
            label: seg.speakerLabel,
            shortLabel: seg.shortLabel,
            role: 'speaker',
            isSpeaking: false,
            lastSpokeAtMs: seg.atMs,
          });
        }
        return {
          id: `final-${index + 1}-${seg.speakerId}`,
          speakerId: seg.speakerId,
          text: seg.text,
          isFinal: true,
          atMs: seg.atMs,
          startMs: seg.startMs,
          endMs: seg.endMs,
          confidence: seg.confidence,
        };
      });
      return {
        transcript,
        speakers,
        partialIndex: {},
        audioLevel: 0,
      };
    }),

  registerSpeaker: (id, label, role = 'speaker', shortLabel) =>
    set((s) => {
      const fallback = makeSpeakerLabels(id, s.speakers.length);
      const existing = s.speakers.find((sp) => sp.id === id);
      if (existing) {
        if (existing.role !== 'unknown') return s;
        return {
          speakers: s.speakers.map((sp) =>
            sp.id === id
              ? {
                  ...sp,
                  label: label ?? fallback.label,
                  shortLabel: shortLabel ?? fallback.shortLabel,
                  role,
                }
              : sp,
          ),
        };
      }
      return {
        speakers: [
          ...s.speakers,
          {
            id,
            label: label ?? fallback.label,
            shortLabel: shortLabel ?? fallback.shortLabel,
            role,
            isSpeaking: false,
            lastSpokeAtMs: 0,
          },
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
  const fallback = makeSpeakerLabels(id, speakers.length);
  return [
    ...speakers,
    {
      id,
      label: fallback.label,
      shortLabel: fallback.shortLabel,
      role: 'speaker',
      isSpeaking: false,
      lastSpokeAtMs: 0,
    },
  ];
}

function makeSpeakerLabels(id: string, currentCount: number): { label: string; shortLabel: string } {
  const parsed = parseSpeakerNumber(id);
  const n = parsed ?? currentCount + 1;
  return { label: `Speaker ${n}`, shortLabel: `SP${n}` };
}

function parseSpeakerNumber(id: string): number | null {
  const match = id.match(/(?:speaker|spk|sp)[-_ ]?0*(\d+)$/i);
  if (!match) return null;
  const n = Number(match[1]);
  if (!Number.isFinite(n)) return null;
  return n === 0 ? 1 : n;
}
