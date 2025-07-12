/**
 * Main App Component for CodeForge
 */
import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';

// Pages
import { LandingPage } from './pages/LandingPage';
import { DashboardPage } from './pages/DashboardPage';
import { ProjectPage } from './pages/ProjectPage';
import { EditorPage } from './pages/EditorPage';
import { LoginPage } from './pages/LoginPage';
import { SignupPage } from './pages/SignupPage';
import { SettingsPage } from './pages/SettingsPage';

// Components
import { ProtectedRoute } from './components/Auth/ProtectedRoute';

// Stores
import { useThemeStore } from './stores/themeStore';
import { useAuthStore } from './stores/authStore';

// Styles
import './styles/globals.css';

// Create query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

export const App: React.FC = () => {
  const { isDarkMode } = useThemeStore();
  const { checkAuth } = useAuthStore();

  useEffect(() => {
    // Check authentication on mount
    checkAuth();
  }, [checkAuth]);

  useEffect(() => {
    // Apply theme class to document
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDarkMode]);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-background text-foreground">
          <Routes>
            {/* Public routes */}
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />

            {/* Protected routes */}
            <Route element={<ProtectedRoute />}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/project/:projectId" element={<ProjectPage />} />
              <Route path="/editor/:projectId" element={<EditorPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Route>

            {/* Catch all */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>

          {/* Global toast notifications */}
          <Toaster
            position="bottom-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: isDarkMode ? '#1f2937' : '#ffffff',
                color: isDarkMode ? '#f3f4f6' : '#111827',
                border: `1px solid ${isDarkMode ? '#374151' : '#e5e7eb'}`,
              },
              success: {
                iconTheme: {
                  primary: '#10b981',
                  secondary: '#ffffff',
                },
              },
              error: {
                iconTheme: {
                  primary: '#ef4444',
                  secondary: '#ffffff',
                },
              },
            }}
          />
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
};