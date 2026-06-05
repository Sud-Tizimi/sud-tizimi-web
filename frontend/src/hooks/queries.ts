/**
 * TanStack Query hooks for the Sud-Tizimi API.
 *
 * Conventions:
 * - All "use*" read hooks return the parsed data directly; if you're not
 *   sure whether the data has loaded, check ``isLoading`` first.
 * - Mutations invalidate the relevant query keys on success so the UI
 *   reflects the change without an extra GET.
 * - "Key factories" keep the invalidation targets in one place.
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';
import { api, apiForm } from '@/lib/api';
import type {
  ActivityEvent,
  AppNotification,
  Case,
  CaseDocument,
  CaseStatus,
  UserPublic,
} from '@/types/domain';

// ---------------------------------------------------------------------------
// Key factories
// ---------------------------------------------------------------------------

export const qk = {
  me: () => ['me'] as const,
  cases: () => ['cases'] as const,
  case: (id: string) => ['case', id] as const,
  caseDocuments: (caseId: string) => ['case', caseId, 'documents'] as const,
  activity: (caseId: string) => ['case', caseId, 'activity'] as const,
  documents: (scope: 'mine' | 'all') => ['documents', scope] as const,
  notifications: () => ['notifications'] as const,
  judges: () => ['users', 'judges'] as const,
  assistants: () => ['users', 'assistants'] as const,
};

// ---------------------------------------------------------------------------
// Response shapes (mirrors Pydantic schemas)
// ---------------------------------------------------------------------------

interface CaseListResponse {
  cases: Case[];
}
interface CaseOneResponse {
  case: Case;
}
interface StatusTransitionApiResponse {
  case: Case;
}
interface ActivityListResponse {
  events: ActivityEvent[];
}
interface NotificationListResponse {
  notifications: AppNotification[];
}
interface UserListJudgesResponse {
  judges: UserPublic[];
}
interface UserListAssistantsResponse {
  assistants: UserPublic[];
}
interface DocumentListResponse {
  documents: CaseDocument[];
}
interface DocumentOneResponse {
  document: CaseDocument;
}

type CaseApiResponse = Case | CaseOneResponse | StatusTransitionApiResponse;
type DocumentApiResponse = CaseDocument | DocumentOneResponse;

function unwrapCaseResponse(response: CaseApiResponse): Case {
  return 'case' in response ? response.case : response;
}

function unwrapDocumentResponse(response: DocumentApiResponse): CaseDocument {
  return 'document' in response ? response.document : response;
}

// ---------------------------------------------------------------------------
// Reads
// ---------------------------------------------------------------------------

export function useCases() {
  return useQuery({
    queryKey: qk.cases(),
    queryFn: async () => (await api<CaseListResponse>('/api/cases')).cases,
  });
}

export function useCase(id: string | null) {
  return useQuery({
    queryKey: id ? qk.case(id) : ['case', 'none'],
    queryFn: async () => unwrapCaseResponse(await api<CaseApiResponse>(`/api/cases/${id}`)),
    enabled: !!id,
  });
}

export function useActivity(caseId: string | null) {
  return useQuery({
    queryKey: caseId ? qk.activity(caseId) : ['activity', 'none'],
    queryFn: async () =>
      (await api<ActivityListResponse>(`/api/activity?caseId=${caseId}`)).events,
    enabled: !!caseId,
  });
}

export function useNotifications() {
  return useQuery({
    queryKey: qk.notifications(),
    queryFn: async () =>
      (await api<NotificationListResponse>('/api/notifications')).notifications,
  });
}

export function useJudges() {
  return useQuery({
    queryKey: qk.judges(),
    queryFn: async () => (await api<UserListJudgesResponse>('/api/users/judges')).judges,
  });
}

export function useAssistants() {
  return useQuery({
    queryKey: qk.assistants(),
    queryFn: async () =>
      (await api<UserListAssistantsResponse>('/api/users/assistants')).assistants,
  });
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

interface CreateCaseInput {
  caseNumber: string;
  citizenName: string;
  description: string;
  assignedJudgeId: string;
}

export function useCreateCase() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: CreateCaseInput) =>
      unwrapCaseResponse(await api<CaseApiResponse>('/api/cases', { method: 'POST', body: input })),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.cases() });
    },
  });
}

export function useSubmitCase(caseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () =>
      unwrapCaseResponse(await api<CaseApiResponse>(`/api/cases/${caseId}/submit`, { method: 'POST' })),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.cases() });
      qc.invalidateQueries({ queryKey: qk.case(caseId) });
      qc.invalidateQueries({ queryKey: qk.activity(caseId) });
      qc.invalidateQueries({ queryKey: qk.notifications() });
    },
  });
}

export function useApproveCase(caseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () =>
      unwrapCaseResponse(await api<CaseApiResponse>(`/api/cases/${caseId}/approve`, { method: 'POST' })),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.cases() });
      qc.invalidateQueries({ queryKey: qk.case(caseId) });
      qc.invalidateQueries({ queryKey: qk.activity(caseId) });
      qc.invalidateQueries({ queryKey: qk.notifications() });
    },
  });
}

export function useReturnCase(caseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (reason: string) =>
      unwrapCaseResponse(
        await api<CaseApiResponse>(`/api/cases/${caseId}/return`, {
          method: 'POST',
          body: { reason },
        }),
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.cases() });
      qc.invalidateQueries({ queryKey: qk.case(caseId) });
      qc.invalidateQueries({ queryKey: qk.activity(caseId) });
      qc.invalidateQueries({ queryKey: qk.notifications() });
    },
  });
}

export function useReopenCase(caseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () =>
      unwrapCaseResponse(await api<CaseApiResponse>(`/api/cases/${caseId}/reopen`, { method: 'POST' })),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.cases() });
      qc.invalidateQueries({ queryKey: qk.case(caseId) });
      qc.invalidateQueries({ queryKey: qk.activity(caseId) });
    },
  });
}

export function useMarkNotificationRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) =>
      await api<AppNotification>(`/api/notifications/${id}/read`, { method: 'POST' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.notifications() });
    },
  });
}

export function useMarkAllNotificationsRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () =>
      await api<{ updated: number }>('/api/notifications/read-all', { method: 'POST' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.notifications() });
    },
  });
}

// Helper used by the notifications bell — count unread
export function unreadCount(notifications: AppNotification[] | undefined): number {
  if (!notifications) return 0;
  return notifications.filter((n) => !n.read).length;
}

// Re-export status ordering for table rendering
export const CASE_STATUSES: CaseStatus[] = [
  'draft',
  'uploaded',
  'under_review',
  'approved',
  'returned',
];

// ---------------------------------------------------------------------------
// Documents — Phase B
// ---------------------------------------------------------------------------

/** List of documents in the user's library.
 *  ``scope='mine'`` (default) returns only the actor's uploads.
 *  ``scope='all'`` returns every document (judges only; the backend 403s
 *  for assistants and the query just stays empty). */
export function useDocuments(scope: 'mine' | 'all' = 'mine') {
  return useQuery({
    queryKey: qk.documents(scope),
    queryFn: async () =>
      (await api<DocumentListResponse>(`/api/documents?scope=${scope}`)).documents,
  });
}

/** Documents attached to a specific case (used by CaseDetail). */
export function useCaseDocuments(caseId: string | null) {
  return useQuery({
    queryKey: caseId ? qk.caseDocuments(caseId) : ['case-documents', 'none'],
    queryFn: async () =>
      (await api<DocumentListResponse>(`/api/cases/${caseId}/documents`)).documents,
    enabled: !!caseId,
  });
}

/** Single document (used by the download action). */
export function useDocument(id: string | null) {
  return useQuery({
    queryKey: ['document', id],
    queryFn: async () =>
      unwrapDocumentResponse(await api<DocumentApiResponse>(`/api/documents/${id}`)),
    enabled: !!id,
  });
}

interface UploadInput {
  file: File;
  caseId?: string | null;
}

/** Upload a document. When ``caseId`` is set, the doc is attached to that
 * case in one step. When ``caseId`` is null/undefined, the doc becomes an
 * orphan and surfaces in ``/documents``. */
export function useUploadDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: UploadInput) => {
      const form = new FormData();
      form.append('file', input.file, input.file.name);
      const path = input.caseId
        ? `/api/cases/${input.caseId}/documents`
        : '/api/documents';
      return unwrapDocumentResponse(await apiForm<DocumentApiResponse>(path, form));
    },
    onSuccess: (doc) => {
      qc.invalidateQueries({ queryKey: ['documents'] });
      if (doc.caseId) {
        qc.invalidateQueries({ queryKey: qk.caseDocuments(doc.caseId) });
        qc.invalidateQueries({ queryKey: qk.case(doc.caseId) });
        qc.invalidateQueries({ queryKey: qk.activity(doc.caseId) });
      }
    },
  });
}

/** Delete a document. The backend removes the file from disk in the
 * same call. 204 is the success code; the mutation does not return a body. */
export function useDeleteDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api<void>(`/api/documents/${id}`, { method: 'DELETE' });
      return id;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['documents'] });
      qc.invalidateQueries({ queryKey: ['case-documents'] });
    },
  });
}

/** Attach an orphan document to a case. */
export function useAttachDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { id: string; caseId: string }) =>
      unwrapDocumentResponse(
        await api<DocumentApiResponse>(`/api/documents/${input.id}/attach`, {
          method: 'POST',
          body: { caseId: input.caseId },
        }),
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['documents'] });
      qc.invalidateQueries({ queryKey: ['case-documents'] });
    },
  });
}

/** Detach a document from its current case. */
export function useDetachDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) =>
      unwrapDocumentResponse(await api<DocumentApiResponse>(`/api/documents/${id}/detach`, { method: 'POST' })),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['documents'] });
      qc.invalidateQueries({ queryKey: ['case-documents'] });
    },
  });
}

/** Trigger a browser download for a document by opening a hidden
 * ``<a download>`` against ``/api/documents/{id}/download`` with the
 * bearer token. We do this client-side so a normal link-click works. */
export function downloadDocumentHref(id: string): string {
  return `/api/documents/${id}/download`;
}
