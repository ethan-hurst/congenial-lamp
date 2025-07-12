/**
 * Project Store - Manages project state
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface Project {
  id: string;
  name: string;
  description?: string;
  language: string;
  framework?: string;
  owner: string;
  collaborationEnabled: boolean;
  isPublic: boolean;
  createdAt: string;
  updatedAt: string;
}

interface ProjectState {
  // Current project
  currentProject: Project | null;
  
  // Recent projects
  recentProjects: Project[];
  
  // Actions
  setCurrentProject: (project: Project | null) => void;
  addRecentProject: (project: Project) => void;
  clearRecentProjects: () => void;
}

export const useProjectStore = create<ProjectState>()(
  persist(
    (set) => ({
      currentProject: null,
      recentProjects: [],
      
      setCurrentProject: (project) => {
        set({ currentProject: project });
        
        // Add to recent if not null
        if (project) {
          set((state) => {
            const filtered = state.recentProjects.filter(p => p.id !== project.id);
            return {
              recentProjects: [project, ...filtered].slice(0, 10), // Keep last 10
            };
          });
        }
      },
      
      addRecentProject: (project) => {
        set((state) => {
          const filtered = state.recentProjects.filter(p => p.id !== project.id);
          return {
            recentProjects: [project, ...filtered].slice(0, 10),
          };
        });
      },
      
      clearRecentProjects: () => {
        set({ recentProjects: [] });
      },
    }),
    {
      name: 'codeforge-projects',
    }
  )
);