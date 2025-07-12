/**
 * Theme Store - Manages application theme
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface ThemeState {
  isDarkMode: boolean;
  accentColor: string;
  
  toggleTheme: () => void;
  setAccentColor: (color: string) => void;
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      isDarkMode: true, // Default to dark mode
      accentColor: '#3b82f6', // Default blue
      
      toggleTheme: () => {
        set((state) => {
          const newMode = !state.isDarkMode;
          
          // Update document class for Tailwind
          if (newMode) {
            document.documentElement.classList.add('dark');
          } else {
            document.documentElement.classList.remove('dark');
          }
          
          return { isDarkMode: newMode };
        });
      },
      
      setAccentColor: (color) => {
        set({ accentColor: color });
        
        // Update CSS variable
        document.documentElement.style.setProperty('--accent-color', color);
      },
    }),
    {
      name: 'codeforge-theme',
      onRehydrateStorage: () => (state) => {
        // Apply theme on load
        if (state?.isDarkMode) {
          document.documentElement.classList.add('dark');
        } else {
          document.documentElement.classList.remove('dark');
        }
        
        if (state?.accentColor) {
          document.documentElement.style.setProperty('--accent-color', state.accentColor);
        }
      },
    }
  )
);