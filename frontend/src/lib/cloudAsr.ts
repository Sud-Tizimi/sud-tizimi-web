import { useCallback, useEffect, useRef, useState } from 'react';
import { getUserMediaOrThrow, toMicrophoneIssue } from '@/lib/microphone';
import type { ASRSegment, ASRTranscriptionResponse } from '@/types/domain';
import type { FinalTranscriptSegment } from '@/stores/sessionStore';
import { useSessionStore } from '@/stores/sessionStore';

const API_BASE: string = (import.meta.env.VITE_API_URL as string | undefined) || '';
const ASR_PROVIDER: string = (import.meta.env.VITE_ASR_PROVIDER as string | undefined) || 'local';

type CloudAsrState = 'idle' | 'recording' | 'processing' | 'done' | 'error';

interface CloudAsrController {
  state: CloudAsrState;
  error: string | null;
  result: ASRTranscriptionResponse | null;
  finalize: () => Promise<ASRTranscriptionResponse | null>;
}

function pickMimeType(): string {
  const candidates = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/mp4',
    'audio/ogg;codecs=opus',
  ];
  return candidates.find((type) => MediaRecorder.isTypeSupported(type)) ?? '';
}

function timestampToMs(ts: string): number {
  const parts = String(ts || '00:00.000').replace(',', '.').split(':').map(Number);
  if (parts.length === 3) {
    return Math.round(((parts[0] * 60 + parts[1]) * 60 + parts[2]) * 1000);
  }
  if (parts.length === 2) {
    return Math.round((parts[0] * 60 + parts[1]) * 1000);
  }
  return 0;
}

function speakerNumber(label: string, fallback: number): number {
  const match = label.match(/(?:speaker|spk|sp)[-_ ]?0*(\d+)/i);
  if (!match) return fallback;
  const n = Number(match[1]);
  return Number.isFinite(n) && n > 0 ? n : fallback;
}

function segmentConfidence(seg: ASRSegment): number | undefined {
  if (!seg.words.length) return undefined;
  return seg.words.reduce((sum, word) => sum + word.confidence, 0) / seg.words.length;
}

function toFinalSegments(segments: ASRSegment[]): FinalTranscriptSegment[] {
  const names = new Map<string, { id: string; label: string; shortLabel: string }>();
  return segments
    .map((seg, index) => {
      const key = seg.speaker || `Speaker ${index + 1}`;
      let speaker = names.get(key);
      if (!speaker) {
        const n = speakerNumber(key, names.size + 1);
        speaker = { id: `speaker-${n}`, label: `Speaker ${n}`, shortLabel: `SP${n}` };
        names.set(key, speaker);
      }
      const atMs = timestampToMs(seg.start);
      return {
        speakerId: speaker.id,
        speakerLabel: speaker.label,
        shortLabel: speaker.shortLabel,
        text: seg.text,
        atMs,
        startMs: atMs,
        endMs: timestampToMs(seg.end),
        confidence: segmentConfidence(seg),
      };
    })
    .filter((seg) => seg.text.trim().length > 0);
}

function recorderBlob(chunks: Blob[], mimeType: string): Blob | null {
  if (!chunks.length) return null;
  return new Blob(chunks, { type: mimeType || chunks[0]?.type || 'audio/webm' });
}

async function stopRecorder(recorder: MediaRecorder | null): Promise<void> {
  if (!recorder || recorder.state === 'inactive') return;
  await new Promise<void>((resolve) => {
    const prev = recorder.onstop;
    recorder.onstop = (event) => {
      prev?.call(recorder, event);
      resolve();
    };
    recorder.stop();
  });
}

export function useCloudAsrRecorder(active: boolean, language: string): CloudAsrController {
  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const mimeRef = useRef('audio/webm');
  const [state, setState] = useState<CloudAsrState>('idle');
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ASRTranscriptionResponse | null>(null);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    chunksRef.current = [];
    setState('recording');
    setError(null);
    setResult(null);

    void getUserMediaOrThrow({ audio: true })
      .then((stream) => {
        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }
        streamRef.current = stream;
        const mimeType = pickMimeType();
        mimeRef.current = mimeType || 'audio/webm';
        const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
        recorderRef.current = recorder;
        recorder.ondataavailable = (event) => {
          if (event.data.size > 0) chunksRef.current.push(event.data);
        };
        recorder.start(1000);
      })
      .catch((e) => {
        setState('error');
        setError(toMicrophoneIssue(e));
      });

    return () => {
      cancelled = true;
      void stopRecorder(recorderRef.current);
      recorderRef.current = null;
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    };
  }, [active]);

  const finalize = useCallback(async () => {
    setError(null);
    await stopRecorder(recorderRef.current);
    recorderRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;

    const blob = recorderBlob(chunksRef.current, mimeRef.current);
    if (!blob) return null;

    setState('processing');
    const form = new FormData();
    form.append('audio', blob, mimeRef.current.includes('mp4') ? 'session.m4a' : 'session.webm');
    form.append('provider', ASR_PROVIDER);
    form.append('language', language.startsWith('uz') ? 'Uzbek' : language.startsWith('ru') ? 'Russian' : 'English');
    form.append('diarize', 'true');

    try {
      const response = await fetch(`${API_BASE}/api/asr/transcribe`, {
        method: 'POST',
        body: form,
      });
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `asr_failed:${response.status}`);
      }
      const data = (await response.json()) as ASRTranscriptionResponse;
      setResult(data);
      useSessionStore.getState().replaceWithFinalSegments(toFinalSegments(data.segments));
      setState('done');
      return data;
    } catch (e) {
      setState('error');
      setError(e instanceof Error ? e.message : 'asr_failed');
      return null;
    }
  }, [language]);

  return { state, error, result, finalize };
}
