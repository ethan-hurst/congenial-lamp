/**
 * Authentication Store
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: string;
  email: string;
  username: string;
  avatar?: string;
  subscription_tier: 'free' | 'pro' | 'team' | 'enterprise';
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  
  // Actions
  login: (user: User, token: string) => void;
  logout: () => void;
  updateUser: (user: Partial<User>) => void;
  checkAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      
      login: (user, token) => {
        set({
          user,
          token,
          isAuthenticated: true,
        });
        
        // Set auth header for API calls
        if (typeof window !== 'undefined') {
          localStorage.setItem('auth_token', token);
        }
      },
      
      logout: () => {
        set({
          user: null,
          token: null,
          isAuthenticated: false,
        });
        
        // Clear auth header
        if (typeof window !== 'undefined') {
          localStorage.removeItem('auth_token');
        }
      },
      
      updateUser: (updates) => {
        set((state) => ({
          user: state.user ? { ...state.user, ...updates } : null,
        }));
      },
      
      checkAuth: () => {
        const token = get().token;
        
        if (token) {
          // TODO: Validate token with backend
          // For now, just check if token exists
          set({ isAuthenticated: true });
        } else {
          set({ isAuthenticated: false });
        }
      },
    }),
    {
      name: 'codeforge-auth',
    }
  )
);