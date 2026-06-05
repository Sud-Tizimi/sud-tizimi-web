/**
 * Auth store — holds the JWT and the current user.
 *
 * Token persists to `localStorage` under `sud-token`. On `bootstrap()` we
 * re-fetch `/api/auth/me` to validate the token and rehydrate the user.
 * The store is intentionally minimal: a Zustand `create()` with
 * persistence handled in a thin wrapper.
 */
import { create } from 'zustand';
import type { UserPublic } from '@/types/domain';
import { api } from '@/lib/api';

const TOKEN_KEY = 'sud-token';

interface AuthState {
  token: string | null;
  user: UserPublic | null;
  /** True after the first `bootstrap()` call has finished. */
  bootstrapped: boolean;
  setSession: (token: string, user: UserPublic) => void;
  clear: () => void;
  /**
   * Rehydrate from localStorage and (if a token exists) call `/api/auth/me`.
   * Idempotent. Returns a promise that resolves when bootstrap is done.
   */
  bootstrap: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: null,
  user: null,
  bootstrapped: false,

  setSession: (token, user) => {
    try {
      localStorage.setItem(TOKEN_KEY, token);
    } catch {
      /* localStorage unavailable — keep token in memory only */
    }
    set({ token, user, bootstrapped: true });
  },

  clear: () => {
    try {
      localStorage.removeItem(TOKEN_KEY);
    } catch {
      /* ignore */
    }
    set({ token: null, user: null, bootstrapped: true });
  },

  bootstrap: async () => {
    if (get().bootstrapped) return;

    let token: string | null = null;
    try {
      token = localStorage.getItem(TOKEN_KEY);
    } catch {
      token = null;
    }
    if (!token) {
      set({ bootstrapped: true });
      return;
    }
    set({ token });
    try {
      const res = await api<{ user: UserPublic }>('/api/auth/me');
      set({ user: res.user, bootstrapped: true });
    } catch {
      // 401 here means the token is stale — clear it so RequireAuth routes
      // us to /login. (The api wrapper already clears on 401, but we
      // additionally reset `user` in case the request threw for a different
      // reason.)
      get().clear();
    }
  },
}));

export function authToken(): string | null {
  return useAuthStore.getState().token;
}
