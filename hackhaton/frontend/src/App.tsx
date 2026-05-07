/**
 * App shell (T020) — QueryClient, BrowserRouter, ErrorBoundary, Toaster, header.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppHeader } from "@/components/chrome/AppHeader";
import { Toaster } from "@/components/ui/toaster";
import { ErrorBoundary } from "@/lib/ErrorBoundary";
import { LiveDiagnosticPage } from "@/pages/LiveDiagnostic/LiveDiagnosticPage";
import { PickerPage } from "@/pages/PickerPage";
import { RunResultPage } from "@/pages/RunResultPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
    mutations: {
      retry: false,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary>
        <BrowserRouter>
          <div className="min-h-dvh">
            <AppHeader />
            <main className="container py-10 sm:py-16">
              <Routes>
                <Route path="/" element={<PickerPage />} />
                <Route path="/host/:hostId" element={<RunResultPage />} />
                <Route path="/live" element={<LiveDiagnosticPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </main>
          </div>
        </BrowserRouter>
        <Toaster />
      </ErrorBoundary>
    </QueryClientProvider>
  );
}
