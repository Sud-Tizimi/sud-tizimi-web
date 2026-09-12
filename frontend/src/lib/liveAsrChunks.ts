import type { ASRSegment, ASRTranscriptionResponse, ASRWord } from '@/types/domain';

export interface CompletedAsrChunk {
  index: number;
  offsetSec: number;
  result: ASRTranscriptionResponse;
}

function timestampToSeconds(value: string): number {
  const parts = String(value || '0').replace(',', '.').split(':').map(Number);
  if (parts.some((part) => !Number.isFinite(part))) return 0;
  if (parts.length === 3) return (parts[0] * 60 + parts[1]) * 60 + parts[2];
  if (parts.length === 2) return parts[0] * 60 + parts[1];
  return parts[0] || 0;
}

function formatTimestamp(totalSeconds: number): string {
  const safe = Math.max(0, totalSeconds);
  const hours = Math.floor(safe / 3600);
  const minutes = Math.floor((safe % 3600) / 60);
  const seconds = (safe % 60).toFixed(3).padStart(6, '0');
  return hours > 0
    ? `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${seconds}`
    : `${String(minutes).padStart(2, '0')}:${seconds}`;
}

function offsetWord(word: ASRWord, offsetSec: number): ASRWord {
  return {
    ...word,
    start: formatTimestamp(timestampToSeconds(word.start) + offsetSec),
    end: formatTimestamp(timestampToSeconds(word.end) + offsetSec),
  };
}

function offsetSegment(segment: ASRSegment, offsetSec: number, id: number): ASRSegment {
  return {
    ...segment,
    id,
    start: formatTimestamp(timestampToSeconds(segment.start) + offsetSec),
    end: formatTimestamp(timestampToSeconds(segment.end) + offsetSec),
    words: segment.words.map((word) => offsetWord(word, offsetSec)),
  };
}

export function mergeCompletedAsrChunks(chunks: CompletedAsrChunk[]): ASRTranscriptionResponse | null {
  const ordered = [...chunks].sort((a, b) => a.index - b.index);
  if (!ordered.length) return null;
  const segments = ordered
    .flatMap((chunk) => chunk.result.segments.map((segment) => ({ segment, offsetSec: chunk.offsetSec })))
    .map(({ segment, offsetSec }, index) => offsetSegment(segment, offsetSec, index + 1));
  const first = ordered[0].result;
  const last = ordered[ordered.length - 1];
  const durationSec = Math.max(
    ...ordered.map((chunk) => chunk.offsetSec + timestampToSeconds(chunk.result.duration)),
    ...segments.map((segment) => timestampToSeconds(segment.end)),
    0,
  );
  const speakers = new Set(segments.map((segment) => segment.speaker).filter(Boolean));
  return {
    ...first,
    provider: last.result.provider,
    model: last.result.model,
    duration: formatTimestamp(durationSec),
    speakersCount: speakers.size || Math.max(...ordered.map((chunk) => chunk.result.speakersCount), 0),
    fullTranscript: segments.map((segment) => segment.text).filter(Boolean).join(' ').trim(),
    processingTimeS: ordered.reduce((sum, chunk) => sum + chunk.result.processingTimeS, 0),
    segments,
  };
}
