/**
 * WebSocket STT client — Checkpoint 1
 *
 * Mirrors the contract of `useMockSttStream(active: boolean)`, so Sessions.tsx
 * can swap between mock and real backend with a single conditional call.
 *
 * Wire contract is defined in `backend/app/core/ws_protocol.py`.
 */
import { useEffect, useRef } from 'react';
import { useSessionStore } from '@/stores/sessionStore';
import { DEMO_SPEAKERS } from '@/lib/mock-data';
import type { SpeakerRole } from '@/types/domain';

type SpeakerSeed = { id: string; label: string; role: SpeakerRole };

// Server WS endpoint. Vite proxy on /ws → ws://localhost:8000 in dev.
const WS_BASE: string =
  (import.meta.env.VITE_WS_URL as string | undefined)?.replace(/\/+$/, '') ||
  '';

function wsUrl(sessionId: string): string {
  return `${WS_BASE}/ws/sessions/${sessionId}`;
}

export function useWsSttStream(active: boolean, sessionId: string | null): void {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<number | null>(null);
  const closedByUs = useRef(false);

  useEffect(() => {
    if (!active || !sessionId) return;

    const store = useSessionStore;
    closedByUs.current = false;

    const connect = () => {
      let ws: WebSocket;
      try {
        ws = new WebSocket(wsUrl(sessionId!));
      } catch (e) {
        // Browser refused to construct — try again in a bit
        reconnectTimer.current = window.setTimeout(connect, 1500);
        return;
      }
      wsRef.current = ws;

      ws.onopen = () => {
        // Idempotent: server treats register_speakers as a no-op for already-known ids
        ws.send(
          JSON.stringify({
            type: 'register_speakers',
            speakers: DEMO_SPEAKERS as SpeakerSeed[],
          }),
        );
      };

      ws.onmessage = (e) => {
        let msg: any;
        try {
          msg = JSON.parse(e.data);
        } catch {
          return;
        }
        const t: string = msg?.type;
        const at: number = typeof msg?.atMs === 'number' ? msg.atMs : Date.now();

        switch (t) {
          case 'session_ready':
            for (const sp of (msg.speakers as SpeakerSeed[]) ?? []) {
              store.getState().registerSpeaker(sp.id, sp.label, sp.role);
            }
            break;
          case 'speaker_registered':
            store
              .getState()
              .registerSpeaker(msg.speaker.id, msg.speaker.label, msg.speaker.role);
            break;
          case 'partial':
            store.getState().upsertPartial(msg.speakerId, msg.text, at);
            break;
          case 'final':
            // Provider's text is already final
            store.getState().upsertPartial(msg.speakerId, msg.text, at);
            store.getState().commitFinalFor(msg.speakerId);
            break;
          case 'audio_level':
            store.getState().setAudioLevel(msg.level);
            break;
          case 'speaker_speaking':
            store.getState().setSpeakerSpeaking(msg.speakerId, msg.speaking);
            break;
          case 'ping':
            try {
              ws.send(JSON.stringify({ type: 'pong', t: msg.t }));
            } catch {
              /* ignore */
            }
            break;
          case 'error':
            // eslint-disable-next-line no-console
            console.warn('[ws] server error', msg.code, msg.message);
            break;
          default:
            break;
        }
      };

      ws.onclose = () => {
        wsRef.current = null;
        if (closedByUs.current) return;
        reconnectTimer.current = window.setTimeout(connect, 1500);
      };

      ws.onerror = () => {
        // close handler will fire next
      };
    };

    connect();

    return () => {
      closedByUs.current = true;
      if (reconnectTimer.current !== null) {
        clearTimeout(reconnectTimer.current);
        reconnectTimer.current = null;
      }
      const ws = wsRef.current;
      wsRef.current = null;
      if (ws && ws.readyState <= 1) {
        try {
          ws.close(1000, 'client_cleanup');
        } catch {
          /* ignore */
        }
      }
      useSessionStore.getState().setAudioLevel(0);
    };
  }, [active, sessionId]);
}
