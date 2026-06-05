/**
 * Tiny fetch wrapper.
 *
 * - Injects `Authorization: Bearer <token>` from the auth store.
 * - On 401, clears the auth store (a stale token, e.g. after the server
 *   restarted or the user was deleted) so the next render routes to /login.
 * - Throws `ApiError` with the parsed `detail` (string) on non-2xx so
 *   TanStack Query / mutations get a clean error.
 */
import { useAuthStore } from '@/stores/authStore';

const API_BASE: string = (import.meta.env.VITE_API_URL as string | undefined) || '';

export class ApiError extends Error {
  status: number;
  detail: string;
  constructor(status: number, detail: string) {
    super(`api_error:${status}:${detail}`);
    this.status = status;
    this.detail = detail;
  }
}

function getToken(): string | null {
  // Read directly from the store (not via the hook) so this works outside React.
  return useAuthStore.getState().token;
}

function clearOnUnauthorized(): void {
  useAuthStore.getState().clear();
  // Use a hard navigation so React Router's effect resets cleanly.
  if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
    window.location.assign('/login');
  }
}

interface RequestOpts extends Omit<RequestInit, 'body'> {
  body?: unknown;
  /** When true, body is sent as JSON; default true if body is not FormData. */
  json?: boolean;
}

export async function api<T>(path: string, opts: RequestOpts = {}): Promise<T> {
  const headers = new Headers(opts.headers ?? {});
  const token = getToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);

  let body: BodyInit | undefined;
  if (opts.body !== undefined) {
    if (opts.body instanceof FormData || opts.json === false) {
      body = opts.body as BodyInit;
    } else {
      headers.set('Content-Type', 'application/json');
      body = JSON.stringify(opts.body);
    }
  }

  const r = await fetch(`${API_BASE}${path}`, { ...opts, headers, body });
  if (r.status === 401) {
    clearOnUnauthorized();
    throw new ApiError(401, 'unauthorized');
  }
  if (!r.ok) {
    let detail = r.statusText;
    // Read body ONCE. Calling r.json() then r.text() throws because the
    // body stream is already consumed.
    try {
      const raw = await r.text();
      try {
        const parsed = JSON.parse(raw) as { detail?: unknown };
        if (parsed && typeof parsed.detail === 'string') {
          detail = parsed.detail;
        } else {
          detail = raw || r.statusText;
        }
      } catch {
        detail = raw || r.statusText;
      }
    } catch {
      /* body read failed — keep statusText */
    }
    throw new ApiError(r.status, detail);
  }
  if (r.status === 204) return undefined as T;
  return (await r.json()) as T;
}

/** Form upload helper — never JSON-encodes the body. */
export function apiForm<T>(path: string, form: FormData): Promise<T> {
  return api<T>(path, { method: 'POST', body: form, json: false });
}
