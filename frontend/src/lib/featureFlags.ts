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

  // Case Management & Document Review module (case-management.md)
  // CP1.5: shipped frontend-only with mock data; full backend in CP2.
  caseDetails: true, // /cases/:id review screen
  caseCreate: true, // /cases/new form for assistants
  documentUpload: true, // in-browser drag-and-drop + AI classification (mock)
  caseWorkflow: true, // submit / approve / return state machine + notifications

  // CP1 — Real-time backend wiring
  useBrowserSpeechStt: true, // local real microphone capture until the production STT API is ready
  useBackendStt: false, // CP1 legacy: FastAPI WebSocket client with scripted mock provider
  useCloudAsrFinalPass: true, // voice-asr-cloud-main integration: final diarized transcript after Stop

  // Phase B — standalone upload + library pages
  upload: true, // /upload — drag-and-drop, optional case picker
  documentsLibrary: true, // /documents — table of my uploads (or all for judges)
  ocrProcessing: true, // /ocr — OCR & Document Processing

  // Phase 27 — SudAI-Law-UZ legal document analysis.
  // Per-document "Analyze" button in DocumentPreview, per-case "AI Analyze all"
  // in CaseDetail PageHeader, and the new "AI legal analysis" section in
  // CaseRightPanel. Gated here so flipping to false reverts the entire
  // surface to plain (pre-SudAI) behaviour in one place.
  aiAnalysis: true,

  // CP2 — HIDDEN FOR MVP (do not enable until Checkpoint 2)
  documents: false, // legacy CP2 flag, kept for compatibility
  aiSummary: false, // AI Summary Center
  notifications: false, // Judicial Notifications Center
  settings: false, // Platform Settings
  mobileShell: false, // Mobile-only routes
} as const;

export type FeatureFlag = keyof typeof ENABLED_FEATURES;

export const isEnabled = (flag: FeatureFlag): boolean => ENABLED_FEATURES[flag];
