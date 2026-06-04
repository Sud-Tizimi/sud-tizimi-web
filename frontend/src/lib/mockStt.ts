import { useEffect, useRef } from 'react';
import { useSessionStore } from '@/stores/sessionStore';
import { DEMO_SPEAKERS } from '@/lib/mock-data';

interface Utterance {
  speakerId: string;
  text: string;
  /** ms from session start when this utterance begins streaming */
  startMs: number;
}

/**
 * Pre-defined courtroom script for the live demo.
 * Times are relative to session start. The whole sequence loops.
 */
const SCRIPT: Utterance[] = [
  { speakerId: 'sp-00', text: 'Суд начинается. Прошу всех встать.', startMs: 500 },
  { speakerId: 'sp-00', text: 'Заседание продолжается. Слушаем истца.', startMs: 4200 },
  { speakerId: 'sp-01', text: 'Уважаемый суд, позвольте изложить обстоятельства дела.', startMs: 7800 },
  { speakerId: 'sp-01', text: 'По нашему мнению, решение администрации было принято с нарушением процедуры.', startMs: 13200 },
  { speakerId: 'sp-00', text: 'Спасибо. Слово предоставляется ответчику.', startMs: 19200 },
  { speakerId: 'sp-02', text: 'Ваша честь, мы не согласны с позицией истца.', startMs: 22200 },
  { speakerId: 'sp-02', text: 'Все процедуры были соблюдены в полном объёме, согласно действующему законодательству.', startMs: 26200 },
  { speakerId: 'sp-03', text: 'Ваша честь, разрешите дополнить позицию стороны истца.', startMs: 32200 },
  { speakerId: 'sp-00', text: 'Пожалуйста.', startMs: 35200 },
  { speakerId: 'sp-03', text: 'Согласно статье 117 Гражданского кодекса, наш клиент имеет безусловное право на компенсацию.', startMs: 37200 },
  { speakerId: 'sp-00', text: 'Суд удаляется на совещание. Прошу всех оставаться на местах.', startMs: 45000 },
  { speakerId: 'sp-01', text: 'Благодарю, Ваша честь.', startMs: 49200 },
];

const PARTIAL_INTERVAL_MS = 450;
const FINAL_DELAY_MS = 1800;
const SCRIPT_LENGTH_MS = 52000;

/**
 * Drives the simulated STT stream into the session store.
 *
 *  active=true  → start streaming partials and committing finals
 *  active=false → no-op (cleanup happens via unmount)
 *
 * Mirrors the API contract of the real WebSocket client we will swap in
 * on Checkpoint 2: { upsertPartial, commitFinal, registerSpeaker }.
 */
export function useMockSttStream(active: boolean): void {
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => {
    if (!active) return;

    const store = useSessionStore;

    // Seed known speakers
    for (const sp of DEMO_SPEAKERS) {
      store.getState().registerSpeaker(sp.id, sp.label, sp.role);
    }

    const loopStart = () => {
      // Clear any pending timers from a previous loop
      timers.current.forEach(clearTimeout);
      timers.current = [];

      for (const u of SCRIPT) {
        // Partial 1
        timers.current.push(
          setTimeout(() => {
            store.getState().upsertPartial(u.speakerId, truncate(u.text, 0.4), u.startMs);
          }, u.startMs),
        );
        // Partial 2 (extended)
        timers.current.push(
          setTimeout(() => {
            store.getState().upsertPartial(u.speakerId, truncate(u.text, 0.75), u.startMs + PARTIAL_INTERVAL_MS);
          }, u.startMs + PARTIAL_INTERVAL_MS),
        );
        // Final
        timers.current.push(
          setTimeout(() => {
            store.getState().upsertPartial(u.speakerId, u.text, u.startMs + FINAL_DELAY_MS);
            store.getState().commitFinalFor(u.speakerId);
          }, u.startMs + FINAL_DELAY_MS),
        );
      }

      // Loop: restart the script after it finishes
      timers.current.push(setTimeout(loopStart, SCRIPT_LENGTH_MS));
    };

    loopStart();

    // Audio-level oscillation: pretend the mic is picking up audio
    const audioTimer = setInterval(() => {
      const level = 30 + Math.random() * 50;
      store.getState().setAudioLevel(level);
    }, 200);

    return () => {
      timers.current.forEach(clearTimeout);
      timers.current = [];
      clearInterval(audioTimer);
      // Silence audio meter on cleanup
      store.getState().setAudioLevel(0);
    };
  }, [active]);
}

function truncate(text: string, ratio: number): string {
  const cut = Math.max(1, Math.floor(text.length * ratio));
  if (cut >= text.length) return text;
  return text.slice(0, cut).trimEnd() + '…';
}
