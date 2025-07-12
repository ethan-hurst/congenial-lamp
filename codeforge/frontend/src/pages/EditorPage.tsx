/**
 * Editor Page Component
 */
import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { CodeEditor } from '../components/Editor/CodeEditor';
import { api } from '../services/api';
import { useProjectStore } from '../stores/projectStore';

export const EditorPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const { setCurrentProject } = useProjectStore();
  const [containerReady, setContainerReady] = useState(false);

  // Fetch project details
  const { data: project, isLoading: projectLoading } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => api.getProject(projectId!),
    enabled: !!projectId,
  });

  // Create container when project loads
  useEffect(() => {
    if (project && !containerReady) {
      createContainer();
    }
  }, [project]);

  // Set current project in store
  useEffect(() => {
    if (project) {
      setCurrentProject(project);
    }
    return () => {
      setCurrentProject(null);
    };
  }, [project, setCurrentProject]);

  const createContainer = async () => {
    try {
      await api.createContainer(projectId!, {
        language: project.language,
        version: 'latest',
        cpu_cores: 2,
        memory_gb: 2,
      });
      setContainerReady(true);
    } catch (error) {
      console.error('Failed to create container:', error);
      // Show error notification
    }
  };

  if (projectLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading project...</p>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <div className="text-center">
          <p className="text-lg text-muted-foreground">Project not found</p>
        </div>
      </div>
    );
  }

  if (!containerReady) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-muted-foreground">Starting development environment...</p>
        </div>
      </div>
    );
  }

  return <CodeEditor projectId={projectId!} />;
};