/**
 * Create Project Modal Component
 */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { HiX } from 'react-icons/hi';
import toast from 'react-hot-toast';

import { api } from '../../services/api';

interface CreateProjectModalProps {
  onClose: () => void;
}

interface ProjectFormData {
  name: string;
  description: string;
  language: string;
  framework: string;
  template: string;
  isPublic: boolean;
}

export const CreateProjectModal: React.FC<CreateProjectModalProps> = ({ onClose }) => {
  const navigate = useNavigate();
  const [isCreating, setIsCreating] = useState(false);
  const { register, handleSubmit, watch, formState: { errors } } = useForm<ProjectFormData>({
    defaultValues: {
      isPublic: true,
      language: 'python',
      template: 'blank',
    },
  });

  const selectedLanguage = watch('language');

  const getFrameworksForLanguage = (language: string): string[] => {
    const frameworks: Record<string, string[]> = {
      python: ['none', 'fastapi', 'django', 'flask', 'jupyter'],
      javascript: ['none', 'react', 'vue', 'angular', 'express', 'next'],
      typescript: ['none', 'react', 'vue', 'angular', 'express', 'next', 'nest'],
      go: ['none', 'gin', 'echo', 'fiber', 'chi'],
      rust: ['none', 'actix', 'rocket', 'warp', 'axum'],
      java: ['none', 'spring', 'quarkus', 'micronaut'],
    };
    return frameworks[language] || ['none'];
  };

  const onSubmit = async (data: ProjectFormData) => {
    setIsCreating(true);
    try {
      const project = await api.createProject(data);
      toast.success('Project created successfully!');
      navigate(`/editor/${project.id}`);
    } catch (error) {
      toast.error('Failed to create project');
      console.error(error);
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
            Create New Project
          </h2>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <HiX className="w-6 h-6" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-6 overflow-y-auto max-h-[calc(90vh-180px)]">
          {/* Project Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Project Name
            </label>
            <input
              {...register('name', { required: 'Project name is required' })}
              type="text"
              className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              placeholder="my-awesome-project"
            />
            {errors.name && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.name.message}</p>
            )}
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Description (optional)
            </label>
            <textarea
              {...register('description')}
              rows={3}
              className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              placeholder="A brief description of your project..."
            />
          </div>

          {/* Language */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Language
            </label>
            <select
              {...register('language')}
              className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="python">Python</option>
              <option value="javascript">JavaScript</option>
              <option value="typescript">TypeScript</option>
              <option value="go">Go</option>
              <option value="rust">Rust</option>
              <option value="java">Java</option>
              <option value="cpp">C++</option>
            </select>
          </div>

          {/* Framework */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Framework (optional)
            </label>
            <select
              {...register('framework')}
              className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              {getFrameworksForLanguage(selectedLanguage).map(framework => (
                <option key={framework} value={framework}>
                  {framework === 'none' ? 'No framework' : framework}
                </option>
              ))}
            </select>
          </div>

          {/* Template */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Template
            </label>
            <div className="grid grid-cols-3 gap-3">
              <label className="relative">
                <input
                  {...register('template')}
                  type="radio"
                  value="blank"
                  className="sr-only peer"
                />
                <div className="p-4 border-2 border-gray-300 dark:border-gray-700 rounded-lg cursor-pointer peer-checked:border-primary-500 peer-checked:bg-primary-50 dark:peer-checked:bg-primary-900/20">
                  <div className="text-center">
                    <div className="text-2xl mb-1">📄</div>
                    <div className="font-medium text-gray-900 dark:text-white">Blank</div>
                    <div className="text-xs text-gray-600 dark:text-gray-400">Start fresh</div>
                  </div>
                </div>
              </label>
              <label className="relative">
                <input
                  {...register('template')}
                  type="radio"
                  value="starter"
                  className="sr-only peer"
                />
                <div className="p-4 border-2 border-gray-300 dark:border-gray-700 rounded-lg cursor-pointer peer-checked:border-primary-500 peer-checked:bg-primary-50 dark:peer-checked:bg-primary-900/20">
                  <div className="text-center">
                    <div className="text-2xl mb-1">🚀</div>
                    <div className="font-medium text-gray-900 dark:text-white">Starter</div>
                    <div className="text-xs text-gray-600 dark:text-gray-400">Basic setup</div>
                  </div>
                </div>
              </label>
              <label className="relative">
                <input
                  {...register('template')}
                  type="radio"
                  value="full"
                  className="sr-only peer"
                />
                <div className="p-4 border-2 border-gray-300 dark:border-gray-700 rounded-lg cursor-pointer peer-checked:border-primary-500 peer-checked:bg-primary-50 dark:peer-checked:bg-primary-900/20">
                  <div className="text-center">
                    <div className="text-2xl mb-1">💎</div>
                    <div className="font-medium text-gray-900 dark:text-white">Full</div>
                    <div className="text-xs text-gray-600 dark:text-gray-400">All features</div>
                  </div>
                </div>
              </label>
            </div>
          </div>

          {/* Visibility */}
          <div>
            <label className="flex items-center space-x-3">
              <input
                {...register('isPublic')}
                type="checkbox"
                className="w-4 h-4 text-primary-600 bg-gray-100 border-gray-300 rounded focus:ring-primary-500 dark:focus:ring-primary-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
              />
              <div>
                <div className="font-medium text-gray-900 dark:text-white">Public Project</div>
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  Anyone can view this project
                </div>
              </div>
            </label>
          </div>
        </form>

        {/* Footer */}
        <div className="flex items-center justify-end space-x-3 p-6 border-t border-gray-200 dark:border-gray-700">
          <button
            type="button"
            onClick={onClose}
            disabled={isCreating}
            className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit(onSubmit)}
            disabled={isCreating}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition disabled:opacity-50"
          >
            {isCreating ? 'Creating...' : 'Create Project'}
          </button>
        </div>
      </div>
    </div>
  );
};