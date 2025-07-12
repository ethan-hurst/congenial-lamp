/**
 * Project Page Component - Shows project details and overview
 */
import React from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { Navbar } from '../components/Layout/Navbar';
import { api } from '../services/api';

export const ProjectPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();

  const { data: project, isLoading } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => api.getProject(projectId!),
    enabled: !!projectId,
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <Navbar />
        <div className="flex items-center justify-center h-96">
          <div className="text-gray-600 dark:text-gray-400">Loading project...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Navbar />
      <div className="container mx-auto px-6 py-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          {project?.name || 'Project'}
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mt-2">
          Project overview and settings will go here.
        </p>
      </div>
    </div>
  );
};