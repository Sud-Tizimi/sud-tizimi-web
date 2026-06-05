import { useEffect, useRef } from 'react';
import { useSessionStore } from '@/stores/sessionStore';

const LIVE_SPEAKER_ID = 'speaker-1';

type SpeechRecognitionCtor = new () => SpeechRecognitionLike;

interface SpeechRecognitionLike {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: { error?: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
}

interface SpeechRecognitionEventLike {
  resultIndex: number;
  results: {
    length: number;
    [index: number]: {
      isFinal: boolean;
      [index: number]: { transcript: string };
    };
  };
}

function getSpeechRecognition(): SpeechRecognitionCtor | null {
  const w = window as typeof window & {
    SpeechRecognition?: SpeechRecognitionCtor;
    webkitSpeechRecognition?: SpeechRecognitionCtor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

function speechLang(language: string): string {
  if (language.startsWith('ru')) return 'ru-RU';
  if (language.startsWith('uz')) return 'uz-UZ';
  return 'en-US';
}

export function useBrowserSpeechStt(active: boolean, language: string): void {
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number | null>(null);
  const startedAtRef = useRef<number>(0);
  const shouldRestartRef = useRef(false);

  useEffect(() => {
    if (!active) return;

    const Recognition = getSpeechRecognition();
    const store = useSessionStore;
    startedAtRef.current = Date.now();
    shouldRestartRef.current = true;

    store.getState().registerSpeaker(LIVE_SPEAKER_ID, 'Speaker 1', 'speaker', 'SP1');

    if (Recognition) {
      const recognition = new Recognition();
      recognitionRef.current = recognition;
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = speechLang(language);

      recognition.onresult = (event) => {
        for (let i = event.resultIndex; i < event.results.length; i += 1) {
          const result = event.results[i];
          const text = result[0]?.transcript?.trim();
          if (!text) continue;

          const atMs = Date.now() - startedAtRef.current;
          store.getState().upsertPartial(LIVE_SPEAKER_ID, text, atMs);
          if (result.isFinal) {
            store.getState().commitFinalFor(LIVE_SPEAKER_ID);
          }
        }
      };

      recognition.onerror = (event) => {
        // eslint-disable-next-line no-console
        console.warn('[browser-speech] recognition error', event.error);
      };

      recognition.onend = () => {
        if (!shouldRestartRef.current) return;
        window.setTimeout(() => {
          if (!shouldRestartRef.current) return;
          try {
            recognition.start();
          } catch {
            /* browser may still be closing the previous recognition instance */
          }
        }, 250);
      };

      try {
        recognition.start();
      } catch (e) {
        // eslint-disable-next-line no-console
        console.warn('[browser-speech] failed to start recognition', e);
      }
    } else {
      // eslint-disable-next-line no-console
      console.warn('[browser-speech] Web Speech API is not supported in this browser');
    }

    let cancelled = false;
    void navigator.mediaDevices
      ?.getUserMedia({ audio: true })
      .then((stream) => {
        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }
        streamRef.current = stream;
        const AudioContextCtor = window.AudioContext;
        const audioContext = new AudioContextCtor();
        audioContextRef.current = audioContext;

        const source = audioContext.createMediaStreamSource(stream);
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        source.connect(analyser);

        const data = new Uint8Array(analyser.frequencyBinCount);
        const updateLevel = () => {
          analyser.getByteFrequencyData(data);
          const avg = data.reduce((sum, value) => sum + value, 0) / data.length;
          store.getState().setAudioLevel(Math.min(100, Math.round((avg / 128) * 100)));
          rafRef.current = window.requestAnimationFrame(updateLevel);
        };
        updateLevel();
      })
      .catch((e) => {
        // eslint-disable-next-line no-console
        console.warn('[browser-speech] microphone unavailable', e);
      });

    return () => {
      cancelled = true;
      shouldRestartRef.current = false;

      const recognition = recognitionRef.current;
      recognitionRef.current = null;
      if (recognition) {
        recognition.onend = null;
        recognition.onresult = null;
        recognition.onerror = null;
        try {
          recognition.stop();
        } catch {
          try {
            recognition.abort();
          } catch {
            /* ignore */
          }
        }
      }

      if (rafRef.current !== null) {
        window.cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      void audioContextRef.current?.close();
      audioContextRef.current = null;

      store.getState().setAudioLevel(0);
      store.getState().setSpeakerSpeaking(LIVE_SPEAKER_ID, false);
    };
  }, [active, language]);
}
