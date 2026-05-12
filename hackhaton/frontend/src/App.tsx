/**
 * App shell (T020) — QueryClient, BrowserRouter, ErrorBoundary, Toaster, header.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppHeader } from "@/components/chrome/AppHeader";
import { AppFooter } from "@/components/chrome/AppFooter";
import { Toaster } from "@/components/ui/toaster";
import { ErrorBoundary } from "@/lib/ErrorBoundary";
import { HostDetailPage } from "@/pages/HostDetailPage";
import { LiveDiagnosticPage } from "@/pages/LiveDiagnostic/LiveDiagnosticPage";
import { PickerPage } from "@/pages/PickerPage";
import { RepairGuidesPage } from "@/pages/RepairGuidesPage";

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
          <div className="flex min-h-dvh flex-col">
            <AppHeader />
            <main className="container flex-1 py-10 sm:py-16">
              <Routes>
                <Route path="/" element={<PickerPage />} />
                <Route path="/host/:hostId" element={<HostDetailPage />} />
                <Route path="/live" element={<LiveDiagnosticPage />} />
                <Route path="/repair-guides" element={<RepairGuidesPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </main>
            <AppFooter />
          </div>
        </BrowserRouter>
        <Toaster />
      </ErrorBoundary>
    </QueryClientProvider>
  );
}
