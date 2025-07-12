/**
 * Template Gallery for Instant Cloning
 */
import React, { useState, useEffect } from 'react';
import {
  HiTemplate,
  HiLightningBolt,
  HiClock,
  HiFolder,
  HiDownload,
  HiCheckCircle
} from 'react-icons/hi';
import { FaReact, FaPython, FaNodeJs, FaRust } from 'react-icons/fa';
import { SiNextdotjs, SiTypescript } from 'react-icons/si';

import { api } from '../../services/api';
import { useProjectStore } from '../../stores/projectStore';

interface Template {
  id: string;
  name: string;
  description: string;
  tags: string[];
  clone_time_estimate: string;
  file_count: number;
  size_mb: number;
}

interface TemplateGalleryProps {
  isOpen: boolean;
  onClose: () => void;
  onTemplateCloned?: (projectId: string) => void;
}

const getTemplateIcon = (templateId: string) => {
  const icons: { [key: string]: React.ReactNode } = {
    'react-typescript': <FaReact className="w-8 h-8 text-blue-500" />,
    'python-fastapi': <FaPython className="w-8 h-8 text-yellow-500" />,
    'node-express': <FaNodeJs className="w-8 h-8 text-green-500" />,
    'fullstack-nextjs': <SiNextdotjs className="w-8 h-8 text-black dark:text-white" />,
    'rust-actix': <FaRust className="w-8 h-8 text-orange-500" />,
  };
  return icons[templateId] || <HiTemplate className="w-8 h-8 text-gray-500" />;
};

const getTagColor = (tag: string) => {
  const colors: { [key: string]: string } = {
    frontend: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    backend: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    fullstack: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
    react: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200',
    python: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    nodejs: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    typescript: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    api: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
    performance: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    rust: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  };
  return colors[tag] || 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
};

export const TemplateGallery: React.FC<TemplateGalleryProps> = ({
  isOpen,
  onClose,
  onTemplateCloned,
}) => {
  const { addProject, setCurrentProject } = useProjectStore();
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [cloning, setCloning] = useState<string | null>(null);
  const [cloneResults, setCloneResults] = useState<Map<string, any>>(new Map());

  useEffect(() => {
    if (isOpen) {
      loadTemplates();
    }
  }, [isOpen]);

  const loadTemplates = async () => {
    try {
      setLoading(true);
      const response = await api.getCloneTemplates();
      setTemplates(response.templates);
    } catch (error) {
      console.error('Failed to load templates:', error);
    } finally {
      setLoading(false);
    }
  };

  const cloneTemplate = async (template: Template, projectName?: string) => {
    setCloning(template.id);
    
    try {
      const response = await api.cloneTemplate(
        template.id,
        projectName || `My ${template.name} Project`
      );

      // Add to results
      setCloneResults(prev => new Map(prev.set(template.id, response)));

      // Add to project store
      addProject({
        id: response.new_project_id,
        name: projectName || `My ${template.name} Project`,
        description: template.description,
        language: template.tags[0] || 'multi',
        template: template.id,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });

      onTemplateCloned?.(response.new_project_id);
    } catch (error) {
      console.error('Template clone failed:', error);
      alert('Failed to clone template. Please try again.');
    } finally {
      setCloning(null);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-r from-primary-500 to-secondary-500 rounded-lg flex items-center justify-center">
              <HiLightningBolt className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                Instant Templates
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Clone production-ready projects in seconds
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <HiTemplate className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center h-48">
              <div className="animate-spin w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full"></div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {templates.map((template) => {
                const result = cloneResults.get(template.id);
                const isCloning = cloning === template.id;
                const isCloned = !!result;

                return (
                  <div
                    key={template.id}
                    className={`border-2 rounded-lg p-6 transition-all ${
                      isCloned
                        ? 'border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20'
                        : 'border-gray-200 dark:border-gray-700 hover:border-primary-300 dark:hover:border-primary-600'
                    }`}
                  >
                    {/* Template Header */}
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center space-x-3">
                        {getTemplateIcon(template.id)}
                        <div>
                          <h3 className="font-semibold text-gray-900 dark:text-white">
                            {template.name}
                          </h3>
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            {template.description}
                          </p>
                        </div>
                      </div>
                      
                      {isCloned && (
                        <HiCheckCircle className="w-6 h-6 text-green-500" />
                      )}
                    </div>

                    {/* Tags */}
                    <div className="flex flex-wrap gap-2 mb-4">
                      {template.tags.map((tag) => (
                        <span
                          key={tag}
                          className={`px-2 py-1 rounded-full text-xs font-medium ${getTagColor(tag)}`}
                        >
                          {tag}
                        </span>
                      ))}
                    </div>

                    {/* Stats */}
                    <div className="grid grid-cols-3 gap-4 mb-4 text-sm">
                      <div className="flex items-center space-x-1 text-gray-600 dark:text-gray-400">
                        <HiClock className="w-4 h-4" />
                        <span>{template.clone_time_estimate}</span>
                      </div>
                      <div className="flex items-center space-x-1 text-gray-600 dark:text-gray-400">
                        <HiFolder className="w-4 h-4" />
                        <span>{template.file_count} files</span>
                      </div>
                      <div className="flex items-center space-x-1 text-gray-600 dark:text-gray-400">
                        <HiDownload className="w-4 h-4" />
                        <span>{template.size_mb}MB</span>
                      </div>
                    </div>

                    {/* Clone Result or Action */}
                    {isCloned ? (
                      <div className="space-y-3">
                        <div className="p-3 bg-green-100 dark:bg-green-900/30 rounded-lg">
                          <div className="flex items-center space-x-2 text-green-800 dark:text-green-200">
                            <HiCheckCircle className="w-4 h-4" />
                            <span className="text-sm font-medium">
                              Cloned in {result.message.match(/(\d+\.\d+)/)?.[1] || '< 1'}s
                            </span>
                          </div>
                        </div>
                        <div className="flex space-x-2">
                          <button
                            onClick={() => cloneTemplate(template)}
                            className="flex-1 px-3 py-2 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition"
                          >
                            Clone Again
                          </button>
                          <button
                            onClick={() => {
                              setCurrentProject(result.new_project_id);
                              onClose();
                            }}
                            className="flex-1 px-3 py-2 text-sm bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition"
                          >
                            Open Project
                          </button>
                        </div>
                      </div>
                    ) : (
                      <button
                        onClick={() => cloneTemplate(template)}
                        disabled={isCloning}
                        className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-primary-600 hover:bg-primary-700 disabled:opacity-50 text-white rounded-lg transition"
                      >
                        {isCloning ? (
                          <>
                            <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
                            <span>Cloning...</span>
                          </>
                        ) : (
                          <>
                            <HiLightningBolt className="w-4 h-4" />
                            <span>Clone Template</span>
                          </>
                        )}
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-500 dark:text-gray-400">
              <div className="flex items-center space-x-2">
                <HiLightningBolt className="w-4 h-4 text-primary-500" />
                <span>Templates are pre-optimized for instant cloning</span>
              </div>
            </div>
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};