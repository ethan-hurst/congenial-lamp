/**
 * Editor Store - Manages editor state and preferences
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface EditorTab {
  id: string;
  filePath: string;
  fileName: string;
  content: string;
  isDirty: boolean;
  language: string;
}

interface EditorState {
  // Tabs
  tabs: EditorTab[];
  activeTabId: string | null;
  
  // Editor preferences
  theme: 'vs' | 'vs-dark' | 'hc-black';
  fontSize: number;
  tabSize: number;
  wordWrap: boolean;
  showLineNumbers: boolean;
  showMinimap: boolean;
  
  // Actions
  openTab: (tab: Omit<EditorTab, 'id'>) => void;
  closeTab: (tabId: string) => void;
  setActiveTab: (tabId: string) => void;
  updateTabContent: (tabId: string, content: string) => void;
  markTabClean: (tabId: string) => void;
  
  // Preferences
  setTheme: (theme: EditorState['theme']) => void;
  setFontSize: (size: number) => void;
  setTabSize: (size: number) => void;
  toggleWordWrap: () => void;
  toggleLineNumbers: () => void;
  toggleMinimap: () => void;
}

export const useEditorStore = create<EditorState>()(
  persist(
    (set, get) => ({
      // Initial state
      tabs: [],
      activeTabId: null,
      
      // Default preferences
      theme: 'vs-dark',
      fontSize: 14,
      tabSize: 2,
      wordWrap: false,
      showLineNumbers: true,
      showMinimap: true,
      
      // Tab management
      openTab: (tabData) => {
        const id = `tab-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const newTab: EditorTab = {
          ...tabData,
          id,
          isDirty: false,
        };
        
        set((state) => ({
          tabs: [...state.tabs, newTab],
          activeTabId: id,
        }));
      },
      
      closeTab: (tabId) => {
        set((state) => {
          const newTabs = state.tabs.filter((tab) => tab.id !== tabId);
          let newActiveTabId = state.activeTabId;
          
          // If closing active tab, switch to next available
          if (state.activeTabId === tabId) {
            const closedIndex = state.tabs.findIndex((tab) => tab.id === tabId);
            if (newTabs.length > 0) {
              const newIndex = Math.min(closedIndex, newTabs.length - 1);
              newActiveTabId = newTabs[newIndex].id;
            } else {
              newActiveTabId = null;
            }
          }
          
          return {
            tabs: newTabs,
            activeTabId: newActiveTabId,
          };
        });
      },
      
      setActiveTab: (tabId) => {
        set({ activeTabId: tabId });
      },
      
      updateTabContent: (tabId, content) => {
        set((state) => ({
          tabs: state.tabs.map((tab) =>
            tab.id === tabId
              ? { ...tab, content, isDirty: true }
              : tab
          ),
        }));
      },
      
      markTabClean: (tabId) => {
        set((state) => ({
          tabs: state.tabs.map((tab) =>
            tab.id === tabId
              ? { ...tab, isDirty: false }
              : tab
          ),
        }));
      },
      
      // Preference setters
      setTheme: (theme) => set({ theme }),
      setFontSize: (fontSize) => set({ fontSize }),
      setTabSize: (tabSize) => set({ tabSize }),
      toggleWordWrap: () => set((state) => ({ wordWrap: !state.wordWrap })),
      toggleLineNumbers: () => set((state) => ({ showLineNumbers: !state.showLineNumbers })),
      toggleMinimap: () => set((state) => ({ showMinimap: !state.showMinimap })),
    }),
    {
      name: 'codeforge-editor-preferences',
      partialize: (state) => ({
        theme: state.theme,
        fontSize: state.fontSize,
        tabSize: state.tabSize,
        wordWrap: state.wordWrap,
        showLineNumbers: state.showLineNumbers,
        showMinimap: state.showMinimap,
      }),
    }
  )
);