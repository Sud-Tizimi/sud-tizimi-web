// ---------------------------------------------------------------------------
// Live-session domain (CP1)
// ---------------------------------------------------------------------------

export type SessionStatus = 'live' | 'completed' | 'paused';

export type SpeakerRole = 'speaker' | 'unknown';

export interface SpeakerProfile {
  id: string;
  label: string;
  shortLabel?: string;
  role: SpeakerRole;
  fullName?: string;
}

// ---------------------------------------------------------------------------
// Case Management & Document Review (CP2 module — implemented frontend-only)
// Spec: Sud-Tizimi/case-management.md
// ---------------------------------------------------------------------------

export type UserRole = 'judge' | 'assistant';

/** Server-side user account — mirrors the Pydantic ``UserPublic`` schema. */
export interface UserPublic {
  id: string;
  email: string;
  fullName: string;
  role: UserRole;
  court?: string | null;
  createdAt: string; // ISO
}

export interface LoginResponse {
  accessToken: string;
  tokenType: 'bearer';
  user: UserPublic;
}

export interface Judge {
  id: string;
  name: string;
  court: string;
}

export interface Assistant {
  id: string;
  name: string;
}

// Workflow statuses as defined in case-management.md §4.
export type CaseStatus =
  | 'draft'
  | 'uploaded'
  | 'under_review'
  | 'approved'
  | 'returned';

// Document categories as defined in case-management.md §7.
export type DocumentCategory =
  | 'procedural'
  | 'participant'
  | 'evidence'
  | 'court';

export type DocumentType =
  // procedural
  | 'claim'
  | 'counterclaim'
  | 'appeal'
  | 'cassation_appeal'
  | 'statement'
  // participant
  | 'explanation'
  | 'objection'
  | 'additional_statement'
  // evidence
  | 'contract'
  | 'financial_document'
  | 'personal_document'
  // court
  | 'court_decision'
  | 'court_resolution'
  | 'hearing_transcript';

export type DocumentFileType = 'pdf' | 'docx' | 'jpg' | 'png';

/**
 * Document as returned by the API. ``caseId`` is nullable: documents
 * uploaded via /upload start out as orphans and may be attached later.
 * ``uploaderId`` + ``uploaderName`` are denormalised on the wire so the
 * /documents table can render names without a second ``/users`` round-trip.
 */
export interface CaseDocument {
  id: string;
  caseId: string | null;
  fileName: string;
  fileType: DocumentFileType;
  /** bytes (server returns `size`; the docs use `size` throughout). */
  size: number;
  category: DocumentCategory;
  detectedType: DocumentType;
  detectedTypeLabel: string;
  aiConfidence: number; // 0..100, or -1 for pending
  uploaderId: string;
  uploaderName?: string;
  uploadedAt: string; // ISO
}

export type ActivityType =
  | 'case_created'
  | 'documents_uploaded'
  | 'documents_classified'
  | 'case_submitted'
  | 'case_approved'
  | 'case_returned'
  | 'document_added'
  | 'document_removed';

export interface ActivityEvent {
  id: string;
  caseId: string;
  type: ActivityType;
  at: string; // ISO
  actorId: string;
  actorName: string;
  actorRole: UserRole;
  /** Free-form key for translation (e.g. 'activity.case_submitted') */
  messageKey: string;
  /** Optional interpolation bag for the translation key */
  meta?: Record<string, string | number>;
}

export interface Case {
  id: string;
  caseNumber: string;
  citizenName: string;
  description: string;
  status: CaseStatus;
  createdAt: string;
  updatedAt: string;
  assignedJudgeId: string;
  assistantId: string;
  /** Optional reason attached when status === 'returned' */
  returnReason?: string;
}

/**
 * Server-side in-app notification — see case-management.md §17.
 * Shape mirrors the Pydantic ``NotificationResponse`` schema.
 */
export type NotificationKind =
  | 'case_submitted_to_judge'
  | 'case_returned_to_assistant'
  | 'case_approved';

export interface AppNotification {
  id: string;
  caseId: string;
  kind: NotificationKind;
  /** i18n key consumed by the bell (`notification.case_*`). */
  messageKey: string;
  read: boolean;
  at: string; // ISO
}

// ---------------------------------------------------------------------------
// i18n key namespaces used by this module
// ---------------------------------------------------------------------------

/** All translation keys consumed by the case-management feature. */
export const I18N_NAMESPACES = [
  'caseMgmt',
  'caseStatus',
  'documentCategory',
  'documentType',
  'activity',
  'notification',
] as const;

export type I18nNamespace = (typeof I18N_NAMESPACES)[number];
