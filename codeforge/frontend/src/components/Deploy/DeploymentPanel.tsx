/**
 * Deployment Panel Component
 */
import React, { useState, useEffect } from 'react';
import {
  HiRocketLaunch,
  HiCloud,
  HiCog,
  HiEye,
  HiRefresh,
  HiX,
  HiCheckCircle,
  HiExclamationTriangle,
  HiClock,
  HiPlay,
  HiStop,
  HiExternalLink,
  HiChartBar
} from 'react-icons/hi2';
import { api } from '../../services/api';
import { useProjectStore } from '../../stores/projectStore';
import { DeploymentLogs } from './DeploymentLogs';
import { ProviderSelector } from './ProviderSelector';

interface Deployment {
  id: string;
  project_id: string;
  status: string;
  provider: string;
  project_type: string;
  url: string | null;
  preview_urls: string[];
  build_id: string | null;
  created_at: string;
  updated_at: string;
  deployed_at: string | null;
  build_time_seconds: number | null;
  deploy_time_seconds: number | null;
  bundle_size_mb: number | null;
  error_message: string | null;
  config: {
    build_command: string | null;
    start_command: string | null;
    output_directory: string | null;
    environment_variables: Record<string, string>;
    domains: string[];
    regions: string[];
    auto_deploy: boolean;
  };
}

interface DeploymentPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export const DeploymentPanel: React.FC<DeploymentPanelProps> = ({ isOpen, onClose }) => {
  const { currentProject } = useProjectStore();
  
  // State
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [providers, setProviders] = useState<any[]>([]);
  const [selectedProvider, setSelectedProvider] = useState('vercel');
  const [selectedDeployment, setSelectedDeployment] = useState<string | null>(null);
  const [showLogs, setShowLogs] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  
  // Advanced configuration
  const [config, setConfig] = useState({
    project_type: 'spa',
    build_command: '',
    start_command: '',
    output_directory: '',
    environment_variables: {} as Record<string, string>,
    domains: [] as string[],
    regions: [] as string[],
    auto_deploy: true
  });

  // Load deployments for current project
  const loadDeployments = async () => {
    if (!currentProject) return;

    try {
      setIsLoading(true);
      const response = await api.getProjectDeployments(currentProject.id);
      setDeployments(response.deployments);
    } catch (error) {
      console.error('Failed to load deployments:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Load available providers
  const loadProviders = async () => {
    try {
      const response = await api.getDeploymentProviders(config.project_type);
      setProviders(response.providers);
    } catch (error) {
      console.error('Failed to load providers:', error);
    }
  };

  // Quick deploy
  const handleQuickDeploy = async () => {
    if (!currentProject) return;

    try {
      setIsLoading(true);
      const response = await api.quickDeploy(currentProject.id, selectedProvider);
      
      if (response.success) {
        await loadDeployments();
        setSelectedDeployment(response.deployment_id);
      }
    } catch (error) {
      console.error('Quick deploy failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Advanced deploy
  const handleAdvancedDeploy = async () => {
    if (!currentProject) return;

    try {
      setIsLoading(true);
      const response = await api.createDeployment({
        project_id: currentProject.id,
        provider: selectedProvider,
        ...config
      });
      
      if (response.success) {
        await loadDeployments();
        setSelectedDeployment(response.deployment_id);
        setShowAdvanced(false);
      }
    } catch (error) {
      console.error('Deploy failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Cancel deployment
  const handleCancelDeployment = async (deploymentId: string) => {
    try {
      await api.cancelDeployment(deploymentId);
      await loadDeployments();
    } catch (error) {
      console.error('Failed to cancel deployment:', error);
    }
  };

  // Redeploy
  const handleRedeploy = async (deploymentId: string) => {
    try {
      setIsLoading(true);
      const response = await api.redeployProject(deploymentId);
      
      if (response.success) {
        await loadDeployments();
        setSelectedDeployment(response.new_deployment_id);
      }
    } catch (error) {
      console.error('Redeploy failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Get status icon and color
  const getStatusDisplay = (status: string) => {
    switch (status) {
      case 'deployed':
        return { icon: HiCheckCircle, color: 'text-green-500', bg: 'bg-green-50 dark:bg-green-900/20' };
      case 'failed':
        return { icon: HiExclamationTriangle, color: 'text-red-500', bg: 'bg-red-50 dark:bg-red-900/20' };
      case 'building':
      case 'deploying':
        return { icon: HiClock, color: 'text-yellow-500', bg: 'bg-yellow-50 dark:bg-yellow-900/20' };
      default:
        return { icon: HiClock, color: 'text-gray-500', bg: 'bg-gray-50 dark:bg-gray-900/20' };
    }
  };

  // Add environment variable
  const addEnvironmentVariable = () => {
    setConfig(prev => ({
      ...prev,
      environment_variables: {
        ...prev.environment_variables,
        '': ''
      }
    }));
  };

  // Update environment variable
  const updateEnvironmentVariable = (oldKey: string, newKey: string, value: string) => {
    setConfig(prev => {
      const newEnvVars = { ...prev.environment_variables };
      delete newEnvVars[oldKey];
      if (newKey) {
        newEnvVars[newKey] = value;
      }
      return {
        ...prev,
        environment_variables: newEnvVars
      };
    });
  };

  useEffect(() => {
    if (isOpen && currentProject) {
      loadDeployments();
      loadProviders();
    }
  }, [isOpen, currentProject]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-6xl h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <HiRocketLaunch className="w-6 h-6 text-primary-600 dark:text-primary-400" />
            <div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                Deploy Project
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                One-click deployment to 10+ cloud providers
              </p>
            </div>
          </div>
          
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <HiX className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Left Panel - Deploy Actions */}
          <div className="w-96 border-r border-gray-200 dark:border-gray-700 p-6">
            <div className="space-y-6">
              {/* Quick Deploy */}
              <div>
                <h3 className="font-semibold text-gray-900 dark:text-white mb-3">
                  Quick Deploy
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                  Deploy with smart defaults - just pick a provider
                </p>
                
                <ProviderSelector
                  providers={providers}
                  selectedProvider={selectedProvider}
                  onSelect={setSelectedProvider}
                  projectType={config.project_type}
                />
                
                <button
                  onClick={handleQuickDeploy}
                  disabled={isLoading || !selectedProvider}
                  className="w-full mt-4 flex items-center justify-center space-x-2 px-4 py-3 bg-primary-600 hover:bg-primary-700 disabled:opacity-50 text-white rounded-lg transition"
                >
                  {isLoading ? (
                    <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
                  ) : (
                    <HiRocketLaunch className="w-4 h-4" />
                  )}
                  <span>Quick Deploy</span>
                </button>
              </div>

              {/* Advanced Configuration */}
              <div>
                <button
                  onClick={() => setShowAdvanced(!showAdvanced)}
                  className="flex items-center space-x-2 text-sm text-primary-600 hover:text-primary-700"
                >
                  <HiCog className="w-4 h-4" />
                  <span>Advanced Configuration</span>
                </button>
                
                {showAdvanced && (
                  <div className="mt-4 space-y-4">
                    {/* Project Type */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Project Type
                      </label>
                      <select
                        value={config.project_type}
                        onChange={(e) => setConfig(prev => ({ ...prev, project_type: e.target.value }))}
                        className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-700"
                      >
                        <option value="static_site">Static Site</option>
                        <option value="spa">Single Page App</option>
                        <option value="node_app">Node.js App</option>
                        <option value="python_app">Python App</option>
                        <option value="docker_app">Docker App</option>
                        <option value="serverless">Serverless</option>
                        <option value="full_stack">Full Stack</option>
                      </select>
                    </div>

                    {/* Build Command */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Build Command
                      </label>
                      <input
                        type="text"
                        placeholder="npm run build"
                        value={config.build_command}
                        onChange={(e) => setConfig(prev => ({ ...prev, build_command: e.target.value }))}
                        className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-700"
                      />
                    </div>

                    {/* Output Directory */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Output Directory
                      </label>
                      <input
                        type="text"
                        placeholder="dist"
                        value={config.output_directory}
                        onChange={(e) => setConfig(prev => ({ ...prev, output_directory: e.target.value }))}
                        className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-700"
                      />
                    </div>

                    {/* Environment Variables */}
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          Environment Variables
                        </label>
                        <button
                          onClick={addEnvironmentVariable}
                          className="text-xs text-primary-600 hover:text-primary-700"
                        >
                          Add Variable
                        </button>
                      </div>
                      <div className="space-y-2 max-h-32 overflow-y-auto">
                        {Object.entries(config.environment_variables).map(([key, value], index) => (
                          <div key={index} className="flex space-x-2">
                            <input
                              type="text"
                              placeholder="KEY"
                              value={key}
                              onChange={(e) => updateEnvironmentVariable(key, e.target.value, value)}
                              className="flex-1 text-xs border border-gray-300 dark:border-gray-600 rounded px-2 py-1 bg-white dark:bg-gray-700"
                            />
                            <input
                              type="text"
                              placeholder="value"
                              value={value}
                              onChange={(e) => updateEnvironmentVariable(key, key, e.target.value)}
                              className="flex-1 text-xs border border-gray-300 dark:border-gray-600 rounded px-2 py-1 bg-white dark:bg-gray-700"
                            />
                          </div>
                        ))}
                      </div>
                    </div>

                    <button
                      onClick={handleAdvancedDeploy}
                      disabled={isLoading}
                      className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-gray-600 hover:bg-gray-700 disabled:opacity-50 text-white rounded-lg transition"
                    >
                      {isLoading ? (
                        <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
                      ) : (
                        <HiCog className="w-4 h-4" />
                      )}
                      <span>Deploy with Config</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Right Panel - Deployments List */}
          <div className="flex-1 flex flex-col">
            {/* Header */}
            <div className="p-6 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-gray-900 dark:text-white">
                  Recent Deployments
                </h3>
                <button
                  onClick={loadDeployments}
                  className="flex items-center space-x-2 text-sm text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200"
                >
                  <HiRefresh className="w-4 h-4" />
                  <span>Refresh</span>
                </button>
              </div>
            </div>

            {/* Deployments List */}
            <div className="flex-1 overflow-auto p-6">
              {isLoading && deployments.length === 0 ? (
                <div className="flex items-center justify-center h-32">
                  <div className="animate-spin w-6 h-6 border-2 border-primary-600 border-t-transparent rounded-full" />
                </div>
              ) : deployments.length === 0 ? (
                <div className="text-center py-12">
                  <HiCloud className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-500 dark:text-gray-400">
                    No deployments yet. Deploy your project to get started!
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {deployments.map((deployment) => {
                    const statusDisplay = getStatusDisplay(deployment.status);
                    const StatusIcon = statusDisplay.icon;
                    
                    return (
                      <div
                        key={deployment.id}
                        className={`p-4 border rounded-lg transition ${
                          selectedDeployment === deployment.id
                            ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                            : 'border-gray-200 dark:border-gray-700'
                        }`}
                      >
                        {/* Deployment Header */}
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center space-x-3">
                            <div className={`p-2 rounded-lg ${statusDisplay.bg}`}>
                              <StatusIcon className={`w-4 h-4 ${statusDisplay.color}`} />
                            </div>
                            <div>
                              <div className="flex items-center space-x-2">
                                <span className="font-medium text-gray-900 dark:text-white">
                                  {deployment.provider.replace('_', ' ').toUpperCase()}
                                </span>
                                <span className="text-xs px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded-full">
                                  {deployment.project_type.replace('_', ' ')}
                                </span>
                              </div>
                              <div className="text-sm text-gray-500 dark:text-gray-400">
                                {new Date(deployment.created_at).toLocaleString()}
                              </div>
                            </div>
                          </div>
                          
                          <div className="flex items-center space-x-2">
                            {deployment.url && (
                              <a
                                href={deployment.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="p-2 text-gray-400 hover:text-primary-600 transition"
                              >
                                <HiExternalLink className="w-4 h-4" />
                              </a>
                            )}
                            
                            <button
                              onClick={() => {
                                setSelectedDeployment(deployment.id);
                                setShowLogs(true);
                              }}
                              className="p-2 text-gray-400 hover:text-primary-600 transition"
                            >
                              <HiEye className="w-4 h-4" />
                            </button>
                            
                            {deployment.status === 'deployed' && (
                              <button
                                onClick={() => handleRedeploy(deployment.id)}
                                className="p-2 text-gray-400 hover:text-green-600 transition"
                              >
                                <HiRefresh className="w-4 h-4" />
                              </button>
                            )}
                            
                            {['pending', 'building', 'deploying'].includes(deployment.status) && (
                              <button
                                onClick={() => handleCancelDeployment(deployment.id)}
                                className="p-2 text-gray-400 hover:text-red-600 transition"
                              >
                                <HiStop className="w-4 h-4" />
                              </button>
                            )}
                          </div>
                        </div>

                        {/* Deployment Status */}
                        <div className="text-sm">
                          <div className="flex items-center justify-between">
                            <span className={`font-medium ${statusDisplay.color}`}>
                              {deployment.status.charAt(0).toUpperCase() + deployment.status.slice(1)}
                            </span>
                            {deployment.build_time_seconds && (
                              <span className="text-gray-500">
                                Build: {deployment.build_time_seconds.toFixed(1)}s
                              </span>
                            )}
                          </div>
                          
                          {deployment.url && (
                            <div className="mt-2">
                              <a
                                href={deployment.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-primary-600 hover:text-primary-700 text-sm"
                              >
                                {deployment.url}
                              </a>
                            </div>
                          )}
                          
                          {deployment.error_message && (
                            <div className="mt-2 text-red-600 text-sm">
                              {deployment.error_message}
                            </div>
                          )}
                        </div>

                        {/* Deployment Metrics */}
                        {deployment.status === 'deployed' && (
                          <div className="mt-3 flex items-center space-x-4 text-xs text-gray-500">
                            {deployment.bundle_size_mb && (
                              <span>Bundle: {deployment.bundle_size_mb.toFixed(1)}MB</span>
                            )}
                            {deployment.deploy_time_seconds && (
                              <span>Deploy: {deployment.deploy_time_seconds.toFixed(1)}s</span>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Deployment Logs Modal */}
        {showLogs && selectedDeployment && (
          <DeploymentLogs
            deploymentId={selectedDeployment}
            isOpen={showLogs}
            onClose={() => setShowLogs(false)}
          />
        )}
      </div>
    </div>
  );
};