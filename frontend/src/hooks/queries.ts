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
  AIAnalysisRecord,
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
  // Phase 27 — SudAI analysis history
  caseAnalysis: (caseId: string) => ['case', caseId, 'ai-analysis'] as const,
  documentAnalysis: (docId: string) => ['document', docId, 'ai-analysis'] as const,
  ocrEngine: () => ['ocr', 'engine'] as const,
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
interface AIAnalysisListResponse {
  records: AIAnalysisRecord[];
}
export interface OcrBox {
  text: string;
  bbox: number[];
  confidence: number;
}
export interface OcrResult {
  text: string;
  boxes: OcrBox[];
  confidence: number;
  engine: string;
  lang: string | null;
  page_number: number;
}
export interface OcrProcessResponse {
  pages: OcrResult[];
  parser: string;
  metadata: Record<string, unknown>;
}
export interface OcrEngineStatus {
  real_engine: boolean;
  active_engine: string;
}

type CaseApiResponse = Case | CaseOneResponse | StatusTransitionApiResponse;
type DocumentApiResponse = CaseDocument | DocumentOneResponse;
type DocumentScope = 'mine' | 'all';

function unwrapCaseResponse(response: CaseApiResponse): Case {
  return 'case' in response ? response.case : response;
}

function unwrapDocumentResponse(response: DocumentApiResponse): CaseDocument {
  return 'document' in response ? response.document : response;
}

function prependDocument(
  current: CaseDocument[] | undefined,
  doc: CaseDocument,
): CaseDocument[] {
  return [doc, ...(current ?? []).filter((item) => item.id !== doc.id)];
}

function replaceDocument(
  current: CaseDocument[] | undefined,
  doc: CaseDocument,
): CaseDocument[] | undefined {
  if (!current) return current;
  const index = current.findIndex((item) => item.id === doc.id);
  if (index === -1) return current;
  const next = [...current];
  next[index] = doc;
  return next;
}

function invalidateDocumentLists(qc: ReturnType<typeof useQueryClient>) {
  (['mine', 'all'] as const satisfies readonly DocumentScope[]).forEach((scope) => {
    qc.invalidateQueries({ queryKey: qk.documents(scope) });
  });
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

interface UpdateCaseInput {
  caseId: string;
  caseNumber?: string;
  citizenName?: string;
  description?: string;
  assignedJudgeId?: string;
}

/** Edit a case. Only the owning assistant can do it, and only while the
 * case is still in ``draft`` or ``returned``. */
export function useUpdateCase() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: UpdateCaseInput) =>
      unwrapCaseResponse(
        await api<CaseApiResponse>(`/api/cases/${input.caseId}`, {
          method: 'PATCH',
          body: {
            ...(input.caseNumber !== undefined ? { caseNumber: input.caseNumber } : {}),
            ...(input.citizenName !== undefined ? { citizenName: input.citizenName } : {}),
            ...(input.description !== undefined ? { description: input.description } : {}),
            ...(input.assignedJudgeId !== undefined
              ? { assignedJudgeId: input.assignedJudgeId }
              : {}),
          },
        }),
      ),
    onSuccess: (caseItem) => {
      qc.invalidateQueries({ queryKey: qk.cases() });
      qc.invalidateQueries({ queryKey: qk.case(caseItem.id) });
      qc.invalidateQueries({ queryKey: qk.activity(caseItem.id) });
    },
  });
}

/** Delete a case. Only the owning assistant can do it, and only while
 * the case is in ``draft``. Attached documents become orphans. */
export function useDeleteCase() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (caseId: string) => {
      await api<void>(`/api/cases/${caseId}`, { method: 'DELETE' });
      return caseId;
    },
    onSuccess: () => {
      // Nuke the whole case subtree (detail + activity + documents) plus
      // the library list — orphan documents surfaced by the delete live
      // under ``['documents', 'mine']`` etc.
      qc.invalidateQueries({ queryKey: qk.cases() });
      qc.invalidateQueries({ queryKey: ['case'] });
      invalidateDocumentLists(qc);
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
      // Update the visible library immediately so a successful upload never
      // looks like it vanished while the follow-up refetch is still pending.
      qc.setQueryData<CaseDocument[]>(qk.documents('mine'), (current) =>
        prependDocument(current, doc),
      );
      qc.setQueryData<CaseDocument[] | undefined>(qk.documents('all'), (current) =>
        prependDocument(current, doc),
      );
      invalidateDocumentLists(qc);
      qc.refetchQueries({ queryKey: qk.documents('mine') });
      if (doc.caseId) {
        const caseId = doc.caseId;
        qc.setQueryData<CaseDocument[]>(qk.caseDocuments(caseId), (current) =>
          prependDocument(current, doc),
        );
        qc.invalidateQueries({ queryKey: qk.caseDocuments(caseId) });
        qc.invalidateQueries({ queryKey: qk.case(caseId) });
        qc.invalidateQueries({ queryKey: qk.activity(caseId) });
        qc.refetchQueries({ queryKey: qk.caseDocuments(caseId) });
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
      // Invalidate the library list AND every case-scoped query (we don't
      // know which case the doc belonged to from here). The ``['case']``
      // prefix matches ``case detail``, ``case documents`` and
      // ``case activity`` keys — see the ``qk`` factory above.
      invalidateDocumentLists(qc);
      qc.invalidateQueries({ queryKey: ['case'] });
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
    onSuccess: (doc, vars) => {
      qc.setQueryData<CaseDocument[] | undefined>(qk.documents('mine'), (current) =>
        replaceDocument(current, doc),
      );
      qc.setQueryData<CaseDocument[] | undefined>(qk.documents('all'), (current) =>
        replaceDocument(current, doc),
      );
      qc.setQueryData<CaseDocument[]>(qk.caseDocuments(vars.caseId), (current) =>
        prependDocument(current, doc),
      );
      invalidateDocumentLists(qc);
      // Only invalidate the case-scoped keys for THIS case.
      qc.invalidateQueries({ queryKey: qk.caseDocuments(vars.caseId) });
      qc.invalidateQueries({ queryKey: qk.case(vars.caseId) });
      qc.invalidateQueries({ queryKey: qk.activity(vars.caseId) });
    },
  });
}

/** Detach a document from its current case. */
export function useDetachDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) =>
      unwrapDocumentResponse(await api<DocumentApiResponse>(`/api/documents/${id}/detach`, { method: 'POST' })),
    onSuccess: (doc) => {
      qc.setQueryData<CaseDocument[] | undefined>(qk.documents('mine'), (current) =>
        replaceDocument(current, doc),
      );
      qc.setQueryData<CaseDocument[] | undefined>(qk.documents('all'), (current) =>
        replaceDocument(current, doc),
      );
      // We don't know which case the doc belonged to from the detach
      // payload, so nuke the whole case subtree like Delete does.
      invalidateDocumentLists(qc);
      qc.invalidateQueries({ queryKey: ['case'] });
    },
  });
}

/** Trigger a browser download for a document by opening a hidden
 * ``<a download>`` against ``/api/documents/{id}/download`` with the
 * bearer token. We do this client-side so a normal link-click works. */
export function downloadDocumentHref(id: string): string {
  return `/api/documents/${id}/download`;
}

// ---------------------------------------------------------------------------
// OCR — engine status + ad-hoc processing
// ---------------------------------------------------------------------------

export function useOcrEngine() {
  return useQuery({
    queryKey: qk.ocrEngine(),
    queryFn: async () => api<OcrEngineStatus>('/api/ocr/engine'),
  });
}

interface OcrUploadInput {
  file: File;
  lang?: string;
}

function appendOcrForm(input: OcrUploadInput): FormData {
  const form = new FormData();
  form.append('file', input.file, input.file.name);
  if (input.lang) form.append('lang', input.lang);
  return form;
}

export function useOcrProcessImage() {
  return useMutation({
    mutationFn: async (input: OcrUploadInput) =>
      apiForm<OcrResult>('/api/ocr/image', appendOcrForm(input)),
  });
}

export function useOcrProcessDocument() {
  return useMutation({
    mutationFn: async (input: OcrUploadInput) =>
      apiForm<OcrProcessResponse>('/api/ocr/process', appendOcrForm(input)),
  });
}

// ---------------------------------------------------------------------------
// Phase 27 — SudAI-Law-UZ analysis (per-case + per-document)
// ---------------------------------------------------------------------------

/** Case-level analysis history. The AI panel reads the *latest* record. */
export function useCaseAnalysis(caseId: string | null) {
  return useQuery({
    queryKey: caseId ? qk.caseAnalysis(caseId) : ['case-ai-analysis', 'none'],
    queryFn: async () => {
      const res = await api<AIAnalysisListResponse>(`/api/cases/${caseId}/analysis`);
      return res.records;
    },
    enabled: !!caseId,
    refetchInterval: (query) => {
      // While a run is pending or running, poll every 2s so the AI panel
      // transitions to the result without a manual refresh. Once we see
      // a terminal status, stop polling.
      const data = query.state.data as AIAnalysisRecord[] | undefined;
      const latest = data?.[0];
      if (!latest) return false;
      return latest.status === 'pending' || latest.status === 'running' ? 2000 : false;
    },
  });
}

/** Document-level analysis history. */
export function useDocumentAnalysis(documentId: string | null) {
  return useQuery({
    queryKey: documentId ? qk.documentAnalysis(documentId) : ['document-ai-analysis', 'none'],
    queryFn: async () => {
      const res = await api<AIAnalysisListResponse>(`/api/documents/${documentId}/analysis`);
      return res.records;
    },
    enabled: !!documentId,
    refetchInterval: (query) => {
      const data = query.state.data as AIAnalysisRecord[] | undefined;
      const latest = data?.[0];
      if (!latest) return false;
      return latest.status === 'pending' || latest.status === 'running' ? 2000 : false;
    },
  });
}

/** Trigger a case-level aggregated analysis. Permission: case-scope. */
export function useAnalyzeCase() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (caseId: string) => {
      const res = await api<AIAnalysisRecord>(`/api/cases/${caseId}/analysis`, { method: 'POST' });
      return res;
    },
    onSuccess: (record) => {
      qc.invalidateQueries({ queryKey: qk.caseAnalysis(record.caseId) });
      qc.invalidateQueries({ queryKey: qk.case(record.caseId) });
      qc.invalidateQueries({ queryKey: qk.activity(record.caseId) });
    },
  });
}

interface AnalyzeDocumentInput {
  documentId: string;
  caseId: string | null;
}

/** Trigger a single-document analysis. Permission: doc-scope. */
export function useAnalyzeDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: AnalyzeDocumentInput) => {
      const res = await api<AIAnalysisRecord>(`/api/documents/${input.documentId}/analysis`, {
        method: 'POST',
      });
      return res;
    },
    onSuccess: (record) => {
      qc.invalidateQueries({ queryKey: qk.documentAnalysis(record.documentId ?? '') });
      qc.invalidateQueries({ queryKey: qk.caseAnalysis(record.caseId) });
      qc.invalidateQueries({ queryKey: qk.case(record.caseId) });
      qc.invalidateQueries({ queryKey: qk.activity(record.caseId) });
    },
  });
}
