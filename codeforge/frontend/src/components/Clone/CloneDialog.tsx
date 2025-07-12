/**
 * Project Clone Dialog
 */
import React, { useState, useEffect } from 'react';
import {
  HiX,
  HiDuplicate,
  HiLightningBolt,
  HiCog,
  HiShieldCheck,
  HiPlay,
  HiCheckCircle,
  HiClock
} from 'react-icons/hi';
import { FaRocket } from 'react-icons/fa';

import { api } from '../../services/api';
import { useProjectStore } from '../../stores/projectStore';

interface CloneOptions {
  cloneName: string;
  includeDependencies: boolean;
  includeContainers: boolean;
  includeSecrets: boolean;
  preserveState: boolean;
}

interface CloneDialogProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
  projectName: string;
  onCloneComplete?: (newProjectId: string) => void;
}

export const CloneDialog: React.FC<CloneDialogProps> = ({
  isOpen,
  onClose,
  projectId,
  projectName,
  onCloneComplete,
}) => {
  const { addProject, setCurrentProject } = useProjectStore();
  const [options, setOptions] = useState<CloneOptions>({
    cloneName: `Clone of ${projectName}`,
    includeDependencies: true,
    includeContainers: true,
    includeSecrets: false,
    preserveState: true,
  });
  
  const [isCloning, setIsCloning] = useState(false);
  const [cloneResult, setCloneResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [estimatedTime, setEstimatedTime] = useState('< 1 second');

  // Update estimated time based on options
  useEffect(() => {
    let baseTime = 0.3;
    if (options.includeDependencies) baseTime += 0.2;
    if (options.includeContainers) baseTime += 0.3;
    if (options.preserveState) baseTime += 0.2;
    
    setEstimatedTime(
      baseTime < 1 ? '< 1 second' : `~${baseTime.toFixed(1)} seconds`
    );
  }, [options]);

  const handleClone = async () => {
    setIsCloning(true);
    setError(null);
    setCloneResult(null);

    try {
      const response = await api.cloneProject({
        project_id: projectId,
        clone_name: options.cloneName || undefined,
        include_dependencies: options.includeDependencies,
        include_containers: options.includeContainers,
        include_secrets: options.includeSecrets,
        preserve_state: options.preserveState,
      });

      setCloneResult(response);
      
      // Add cloned project to store
      addProject({
        id: response.new_project_id,
        name: options.cloneName,
        description: `Cloned from ${projectName}`,
        language: 'multi',
        template: 'clone',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });

      onCloneComplete?.(response.new_project_id);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Clone failed');
    } finally {
      setIsCloning(false);
    }
  };

  const handleQuickClone = async () => {
    setIsCloning(true);
    setError(null);
    setCloneResult(null);

    try {
      const response = await api.quickClone(projectId);
      setCloneResult(response);
      
      // Add cloned project to store
      addProject({
        id: response.new_project_id,
        name: `Quick Clone of ${projectName}`,
        description: `Ultra-fast clone of ${projectName}`,
        language: 'multi',
        template: 'clone',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });

      onCloneComplete?.(response.new_project_id);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Quick clone failed');
    } finally {
      setIsCloning(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-md mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-2">
            <HiDuplicate className="w-6 h-6 text-primary-600 dark:text-primary-400" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Clone Project
            </h3>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <HiX className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {!cloneResult ? (
            <>
              {/* Project Info */}
              <div className="mb-6">
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                  Cloning project:
                </p>
                <p className="font-medium text-gray-900 dark:text-white">
                  {projectName}
                </p>
              </div>

              {/* Quick Clone Option */}
              <div className="mb-6 p-4 bg-gradient-to-r from-primary-50 to-secondary-50 dark:from-primary-900/20 dark:to-secondary-900/20 rounded-lg border border-primary-200 dark:border-primary-800">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <HiLightningBolt className="w-5 h-5 text-primary-600" />
                    <span className="font-medium text-primary-900 dark:text-primary-100">
                      Quick Clone
                    </span>
                  </div>
                  <span className="text-xs bg-primary-100 dark:bg-primary-800 text-primary-800 dark:text-primary-200 px-2 py-1 rounded">
                    &lt; 0.5s
                  </span>
                </div>
                <p className="text-sm text-primary-700 dark:text-primary-300 mb-3">
                  Ultra-fast clone with files only. Perfect for quick experiments.
                </p>
                <button
                  onClick={handleQuickClone}
                  disabled={isCloning}
                  className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:opacity-50 text-white rounded-lg transition"
                >
                  {isCloning ? (
                    <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
                  ) : (
                    <FaRocket className="w-4 h-4" />
                  )}
                  <span>Quick Clone</span>
                </button>
              </div>

              {/* Divider */}
              <div className="flex items-center mb-6">
                <div className="flex-1 border-t border-gray-300 dark:border-gray-600"></div>
                <span className="px-3 text-sm text-gray-500 dark:text-gray-400">or</span>
                <div className="flex-1 border-t border-gray-300 dark:border-gray-600"></div>
              </div>

              {/* Custom Clone Options */}
              <div className="space-y-4 mb-6">
                <h4 className="font-medium text-gray-900 dark:text-white">Custom Clone</h4>
                
                {/* Clone Name */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Project Name
                  </label>
                  <input
                    type="text"
                    value={options.cloneName}
                    onChange={(e) => setOptions(prev => ({ ...prev, cloneName: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    placeholder="Enter clone name..."
                  />
                </div>

                {/* Options */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <HiCog className="w-4 h-4 text-gray-500" />
                      <span className="text-sm text-gray-700 dark:text-gray-300">
                        Include Dependencies
                      </span>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={options.includeDependencies}
                        onChange={(e) => setOptions(prev => ({ ...prev, includeDependencies: e.target.checked }))}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 dark:peer-focus:ring-primary-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary-600"></div>
                    </label>
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <HiPlay className="w-4 h-4 text-gray-500" />
                      <span className="text-sm text-gray-700 dark:text-gray-300">
                        Include Containers
                      </span>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={options.includeContainers}
                        onChange={(e) => setOptions(prev => ({ ...prev, includeContainers: e.target.checked }))}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 dark:peer-focus:ring-primary-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary-600"></div>
                    </label>
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <HiShieldCheck className="w-4 h-4 text-gray-500" />
                      <span className="text-sm text-gray-700 dark:text-gray-300">
                        Include Secrets
                      </span>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={options.includeSecrets}
                        onChange={(e) => setOptions(prev => ({ ...prev, includeSecrets: e.target.checked }))}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 dark:peer-focus:ring-primary-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary-600"></div>
                    </label>
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <HiClock className="w-4 h-4 text-gray-500" />
                      <span className="text-sm text-gray-700 dark:text-gray-300">
                        Preserve State
                      </span>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={options.preserveState}
                        onChange={(e) => setOptions(prev => ({ ...prev, preserveState: e.target.checked }))}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 dark:peer-focus:ring-primary-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary-600"></div>
                    </label>
                  </div>
                </div>

                {/* Estimated Time */}
                <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    Estimated time:
                  </span>
                  <span className="text-sm font-medium text-gray-900 dark:text-white">
                    {estimatedTime}
                  </span>
                </div>
              </div>

              {/* Error Display */}
              {error && (
                <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                  <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
                </div>
              )}

              {/* Actions */}
              <div className="flex space-x-3">
                <button
                  onClick={onClose}
                  className="flex-1 px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  onClick={handleClone}
                  disabled={isCloning || !options.cloneName.trim()}
                  className="flex-1 flex items-center justify-center space-x-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:opacity-50 text-white rounded-lg transition"
                >
                  {isCloning ? (
                    <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
                  ) : (
                    <HiDuplicate className="w-4 h-4" />
                  )}
                  <span>Clone Project</span>
                </button>
              </div>
            </>
          ) : (
            /* Success Result */
            <div className="text-center">
              <div className="w-16 h-16 bg-green-100 dark:bg-green-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <HiCheckCircle className="w-8 h-8 text-green-600 dark:text-green-400" />
              </div>
              
              <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                Clone Successful!
              </h4>
              
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                {cloneResult.message}
              </p>

              {cloneResult.performance && (
                <div className="grid grid-cols-2 gap-4 mb-6 text-sm">
                  <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-lg">
                    <div className="font-medium text-gray-900 dark:text-white">
                      {cloneResult.cloned_files || cloneResult.performance?.files_cloned || 0}
                    </div>
                    <div className="text-gray-500 dark:text-gray-400">Files</div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-lg">
                    <div className="font-medium text-gray-900 dark:text-white">
                      {cloneResult.total_time_seconds?.toFixed(3) || cloneResult.performance?.time_seconds?.toFixed(3)}s
                    </div>
                    <div className="text-gray-500 dark:text-gray-400">Time</div>
                  </div>
                </div>
              )}

              <div className="flex space-x-3">
                <button
                  onClick={onClose}
                  className="flex-1 px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition"
                >
                  Close
                </button>
                <button
                  onClick={() => {
                    setCurrentProject(cloneResult.new_project_id);
                    onClose();
                  }}
                  className="flex-1 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition"
                >
                  Open Project
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};