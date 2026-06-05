/**
 * Single shared QueryClient. Defaults are tuned for an internal admin
 * dashboard: short staleTime (server data is small + frequently changes),
 * no refetch-on-window-focus (annoying for case workers), and retry once
 * for transient network errors.
 */
import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60_000,
      refetchOnWindowFocus: false,
      retry: 1,
    },
    mutations: {
      retry: 0,
    },
  },
});
