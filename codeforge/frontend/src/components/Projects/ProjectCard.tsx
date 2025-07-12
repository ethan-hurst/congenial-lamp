/**
 * Project Card Component
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import {
  HiCode,
  HiClock,
  HiUsers,
  HiGlobeAlt,
  HiLockClosed,
  HiDotsVertical
} from 'react-icons/hi';

interface Project {
  id: string;
  name: string;
  description?: string;
  language: string;
  framework?: string;
  isPublic: boolean;
  lastAccessed?: string;
  collaborators?: string[];
}

interface ProjectCardProps {
  project: Project;
}

export const ProjectCard: React.FC<ProjectCardProps> = ({ project }) => {
  const getLanguageColor = (language: string): string => {
    const colors: Record<string, string> = {
      python: 'bg-blue-500',
      javascript: 'bg-yellow-500',
      typescript: 'bg-blue-600',
      go: 'bg-cyan-500',
      rust: 'bg-orange-600',
      java: 'bg-red-600',
      cpp: 'bg-pink-600',
    };
    return colors[language.toLowerCase()] || 'bg-gray-500';
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm hover:shadow-md transition-shadow">
      <div className="p-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div className={`w-10 h-10 rounded-lg ${getLanguageColor(project.language)} flex items-center justify-center`}>
              <HiCode className="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-white">
                {project.name}
              </h3>
              <div className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
                <span>{project.language}</span>
                {project.framework && (
                  <>
                    <span>•</span>
                    <span>{project.framework}</span>
                  </>
                )}
              </div>
            </div>
          </div>
          <button className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
            <HiDotsVertical className="w-5 h-5" />
          </button>
        </div>

        {/* Description */}
        {project.description && (
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4 line-clamp-2">
            {project.description}
          </p>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4 text-sm text-gray-500 dark:text-gray-500">
            <div className="flex items-center space-x-1">
              {project.isPublic ? (
                <HiGlobeAlt className="w-4 h-4" />
              ) : (
                <HiLockClosed className="w-4 h-4" />
              )}
              <span>{project.isPublic ? 'Public' : 'Private'}</span>
            </div>
            {project.lastAccessed && (
              <div className="flex items-center space-x-1">
                <HiClock className="w-4 h-4" />
                <span>{formatDistanceToNow(new Date(project.lastAccessed), { addSuffix: true })}</span>
              </div>
            )}
            {project.collaborators && project.collaborators.length > 0 && (
              <div className="flex items-center space-x-1">
                <HiUsers className="w-4 h-4" />
                <span>{project.collaborators.length}</span>
              </div>
            )}
          </div>
          <Link
            to={`/editor/${project.id}`}
            className="px-3 py-1 text-sm bg-primary-600 text-white rounded hover:bg-primary-700 transition"
          >
            Open
          </Link>
        </div>
      </div>
    </div>
  );
};