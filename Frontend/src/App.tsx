import { useEffect } from "react";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ThemeProvider } from "next-themes";
import { useAuthStore } from "@/stores/authStore";
import { apiClient } from "@/services/api";

// Pages
import Index from "./pages/Index";
import Login from "./pages/Login";
import Chat from "./pages/Chat";
import NotFound from "./pages/NotFound";

// Admin Pages
import AdminLayout from "./components/admin/AdminLayout";
import AdminDashboard from "./pages/admin/AdminDashboard";
import AdminMetrics from "./pages/admin/AdminMetrics";
import AdminApiRequests from "./pages/admin/AdminApiRequests";
import AdminAnswerQuality from "./pages/admin/AdminAnswerQuality";
import AdminUsers from "./pages/admin/AdminUsers";
import AdminSettings from "./pages/admin/AdminSettings";

// Protected Route Component
import ProtectedRoute from "./components/ProtectedRoute";

const queryClient = new QueryClient();

// Component to restore token on app startup and handle auth expiration
const TokenRestorer = () => {
  const { logout } = useAuthStore();
  
  useEffect(() => {
    // Restaurer le token si l'utilisateur est déjà authentifié
    const token = localStorage.getItem('auth_token');
    if (token) {
      apiClient.setToken(token);
    }

    // Écouter l'événement d'expiration de session
    const handleAuthExpired = () => {
      logout();
      // Rediriger vers la page de login si on n'y est pas déjà
      if (window.location.pathname !== '/login' && window.location.pathname !== '/') {
        window.location.href = '/login';
      }
    };

    window.addEventListener('auth:expired', handleAuthExpired);

    // Nettoyer l'écouteur au démontage
    return () => {
      window.removeEventListener('auth:expired', handleAuthExpired);
    };
  }, [logout]);
  
  return null;
};

const App = () => (
  <QueryClientProvider client={queryClient}>
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <TooltipProvider>
        <TokenRestorer />
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <Routes>
            {/* Public routes */}
            <Route path="/" element={<Index />} />
            <Route path="/login" element={<Login />} />

            {/* User routes */}
            <Route
              path="/chat"
              element={
                <ProtectedRoute allowedRoles={["user", "admin"]}>
                  <Chat />
                </ProtectedRoute>
              }
            />

            {/* Admin routes */}
            <Route
              path="/admin"
              element={
                <ProtectedRoute allowedRoles={["admin"]}>
                  <AdminLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Navigate to="/admin/dashboard" replace />} />
              <Route path="dashboard" element={<AdminDashboard />} />
              <Route path="metrics" element={<AdminMetrics />} />
              <Route path="api-requests" element={<AdminApiRequests />} />
              <Route path="answer-quality" element={<AdminAnswerQuality />} />
              <Route path="users" element={<AdminUsers />} />
              <Route path="settings" element={<AdminSettings />} />
            </Route>

            {/* Catch all */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </ThemeProvider>
  </QueryClientProvider>
);

export default App;
