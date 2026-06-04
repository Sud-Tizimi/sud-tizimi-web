/**
 * Feature flags — Checkpoint 1 (MVP)
 *
 * Включены только модули, которые реально работают на демо.
 * Все остальные модули оставлены в коде, но скрыты из UI и роутинга.
 *
 * Чтобы вернуть фичу на Checkpoint 2 — поменять флаг на `true`.
 */

export const ENABLED_FEATURES = {
  // CP1 — MVP (visible)
  dashboard: true,
  sessions: true, // Live Court Session Monitoring
  cases: true, // Case list (read-only, no detail page in CP1)

  // CP1 — Real-time backend wiring
  useBackendStt: true, // CP1: use FastAPI WebSocket client instead of in-browser mock

  // CP2 — HIDDEN FOR MVP (do not enable until Checkpoint 2)
  documents: false, // OCR & Document Processing
  aiSummary: false, // AI Summary Center
  notifications: false, // Judicial Notifications Center
  settings: false, // Platform Settings
  caseDetails: false, // /cases/:id detail page
  mobileShell: false, // Mobile-only routes
} as const;

export type FeatureFlag = keyof typeof ENABLED_FEATURES;

export const isEnabled = (flag: FeatureFlag): boolean => ENABLED_FEATURES[flag];
