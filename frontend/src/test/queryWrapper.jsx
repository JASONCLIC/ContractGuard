import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

/**
 * Build a fresh QueryClient + Provider wrapper for hook tests so each test
 * gets isolated cache and zero retries (failed queries should not retry in
 * unit tests).
 */
export function makeQueryWrapper() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0, staleTime: 0 },
      mutations: { retry: false },
    },
  });
  function Wrapper({ children }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  }
  return { client, Wrapper };
}
