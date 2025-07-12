/**
 * Performance Monitoring Dashboard
 */
import React, { useState, useEffect } from 'react';
import {
  HiChartBar,
  HiCpuChip,
  HiCircleStack,
  HiServerStack,
  HiExclamationTriangle,
  HiCheckCircle,
  HiClock,
  HiArrowPath,
  HiEye,
  HiX,
  HiInformationCircle,
  HiLightBulb,
  HiCloud,
  HiGlobeAlt
} from 'react-icons/hi2';
import { api } from '../../services/api';

interface SystemHealth {
  status: string;
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  active_containers: number;
  active_users: number;
  api_latency_p95: number;
  uptime_seconds: number;
  alerts_count: number;
}

interface Alert {
  id: string;
  metric_type: string;
  threshold: number;
  current_value: number;
  severity: string;
  message: string;
  created_at: string;
  resolved_at?: string;
}

interface Insight {
  type: string;
  severity: string;
  title: string;
  description: string;
  recommendation: string;
  metric_type: string;
  value: number;
}

interface DashboardData {
  system_health: SystemHealth;
  recent_metrics: {
    cpu: { value: number; count: number };
    memory: { value: number; count: number };
    disk: { value: number; count: number };
    api_latency: { value: number; count: number };
  };
  alerts: Alert[];
  insights: Insight[];
  uptime: number;
}

interface PerformanceDashboardProps {
  isOpen: boolean;
  onClose: () => void;
}

export const PerformanceDashboard: React.FC<PerformanceDashboardProps> = ({ isOpen, onClose }) => {
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedTab, setSelectedTab] = useState<'overview' | 'metrics' | 'alerts' | 'insights'>('overview');
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Load dashboard data
  const loadDashboardData = async () => {
    try {
      setIsLoading(true);
      const response = await api.getPerformanceDashboard();
      setDashboardData(response);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Resolve alert
  const resolveAlert = async (alertId: string) => {
    try {
      await api.resolvePerformanceAlert(alertId);
      await loadDashboardData(); // Refresh data
    } catch (error) {
      console.error('Failed to resolve alert:', error);
    }
  };

  // Get status color
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'text-green-500';
      case 'degraded':
        return 'text-yellow-500';
      case 'critical':
        return 'text-red-500';
      default:
        return 'text-gray-500';
    }
  };

  // Get usage color based on percentage
  const getUsageColor = (usage: number) => {
    if (usage >= 90) return 'text-red-500';
    if (usage >= 75) return 'text-yellow-500';
    if (usage >= 50) return 'text-blue-500';
    return 'text-green-500';
  };

  // Get severity color
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'text-red-500 bg-red-50 dark:bg-red-900/20';
      case 'high':
        return 'text-red-400 bg-red-50 dark:bg-red-900/20';
      case 'medium':
        return 'text-yellow-500 bg-yellow-50 dark:bg-yellow-900/20';
      case 'low':
        return 'text-blue-500 bg-blue-50 dark:bg-blue-900/20';
      default:
        return 'text-gray-500 bg-gray-50 dark:bg-gray-900/20';
    }
  };

  // Format uptime
  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (days > 0) {
      return `${days}d ${hours}h ${minutes}m`;
    } else if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else {
      return `${minutes}m`;
    }
  };

  // Auto-refresh effect
  useEffect(() => {
    if (isOpen) {
      loadDashboardData();
      
      if (autoRefresh) {
        const interval = setInterval(loadDashboardData, 30000); // Refresh every 30 seconds
        return () => clearInterval(interval);
      }
    }
  }, [isOpen, autoRefresh]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-7xl h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <HiChartBar className="w-6 h-6 text-primary-600 dark:text-primary-400" />
            <div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                Performance Dashboard
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Real-time system monitoring and analytics
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            {/* Auto-refresh toggle */}
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded border-gray-300 dark:border-gray-600"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">Auto-refresh</span>
            </label>
            
            {/* Refresh button */}
            <button
              onClick={loadDashboardData}
              disabled={isLoading}
              className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              <HiArrowPath className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
            
            {/* Close button */}
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              <HiX className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="border-b border-gray-200 dark:border-gray-700">
          <nav className="flex space-x-8 px-6">
            {[
              { id: 'overview', label: 'Overview', icon: HiChartBar },
              { id: 'metrics', label: 'Metrics', icon: HiCpuChip },
              { id: 'alerts', label: 'Alerts', icon: HiExclamationTriangle },
              { id: 'insights', label: 'Insights', icon: HiLightBulb },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setSelectedTab(tab.id as any)}
                className={`flex items-center space-x-2 py-4 px-2 border-b-2 font-medium text-sm ${
                  selectedTab === tab.id
                    ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                <span>{tab.label}</span>
                {/* Alert count badge */}
                {tab.id === 'alerts' && dashboardData?.alerts.length > 0 && (
                  <span className="inline-flex items-center justify-center px-2 py-1 text-xs font-bold leading-none text-red-100 bg-red-600 rounded-full">
                    {dashboardData.alerts.length}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {isLoading && !dashboardData ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin w-8 h-8 border-2 border-primary-600 border-t-transparent rounded-full" />
            </div>
          ) : !dashboardData ? (
            <div className="flex items-center justify-center h-64 text-gray-500">
              Failed to load dashboard data
            </div>
          ) : (
            <>
              {/* Overview Tab */}
              {selectedTab === 'overview' && (
                <div className="space-y-6">
                  {/* System Health Cards */}
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    {/* Overall Status */}
                    <div className="bg-white dark:bg-gray-700 p-6 rounded-lg border border-gray-200 dark:border-gray-600">
                      <div className="flex items-center">
                        <div className={`p-3 rounded-lg bg-gray-100 dark:bg-gray-600 ${getStatusColor(dashboardData.system_health.status)}`}>
                          {dashboardData.system_health.status === 'healthy' ? (
                            <HiCheckCircle className="w-6 h-6" />
                          ) : (
                            <HiExclamationTriangle className="w-6 h-6" />
                          )}
                        </div>
                        <div className="ml-4">
                          <p className="text-sm font-medium text-gray-600 dark:text-gray-400">System Status</p>
                          <p className={`text-lg font-semibold capitalize ${getStatusColor(dashboardData.system_health.status)}`}>
                            {dashboardData.system_health.status}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* CPU Usage */}
                    <div className="bg-white dark:bg-gray-700 p-6 rounded-lg border border-gray-200 dark:border-gray-600">
                      <div className="flex items-center">
                        <div className={`p-3 rounded-lg bg-gray-100 dark:bg-gray-600 ${getUsageColor(dashboardData.system_health.cpu_usage)}`}>
                          <HiCpuChip className="w-6 h-6" />
                        </div>
                        <div className="ml-4">
                          <p className="text-sm font-medium text-gray-600 dark:text-gray-400">CPU Usage</p>
                          <p className={`text-lg font-semibold ${getUsageColor(dashboardData.system_health.cpu_usage)}`}>
                            {dashboardData.system_health.cpu_usage.toFixed(1)}%
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Memory Usage */}
                    <div className="bg-white dark:bg-gray-700 p-6 rounded-lg border border-gray-200 dark:border-gray-600">
                      <div className="flex items-center">
                        <div className={`p-3 rounded-lg bg-gray-100 dark:bg-gray-600 ${getUsageColor(dashboardData.system_health.memory_usage)}`}>
                          <HiCircleStack className="w-6 h-6" />
                        </div>
                        <div className="ml-4">
                          <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Memory Usage</p>
                          <p className={`text-lg font-semibold ${getUsageColor(dashboardData.system_health.memory_usage)}`}>
                            {dashboardData.system_health.memory_usage.toFixed(1)}%
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Active Containers */}
                    <div className="bg-white dark:bg-gray-700 p-6 rounded-lg border border-gray-200 dark:border-gray-600">
                      <div className="flex items-center">
                        <div className="p-3 rounded-lg bg-gray-100 dark:bg-gray-600 text-blue-500">
                          <HiServerStack className="w-6 h-6" />
                        </div>
                        <div className="ml-4">
                          <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Active Containers</p>
                          <p className="text-lg font-semibold text-gray-900 dark:text-white">
                            {dashboardData.system_health.active_containers}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* System Stats */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Resource Usage */}
                    <div className="bg-white dark:bg-gray-700 p-6 rounded-lg border border-gray-200 dark:border-gray-600">
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Resource Usage</h3>
                      <div className="space-y-4">
                        {/* CPU Progress Bar */}
                        <div>
                          <div className="flex justify-between text-sm mb-1">
                            <span>CPU</span>
                            <span>{dashboardData.system_health.cpu_usage.toFixed(1)}%</span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div
                              className={`h-2 rounded-full ${
                                dashboardData.system_health.cpu_usage >= 80 ? 'bg-red-500' :
                                dashboardData.system_health.cpu_usage >= 60 ? 'bg-yellow-500' : 'bg-green-500'
                              }`}
                              style={{ width: `${Math.min(dashboardData.system_health.cpu_usage, 100)}%` }}
                            />
                          </div>
                        </div>

                        {/* Memory Progress Bar */}
                        <div>
                          <div className="flex justify-between text-sm mb-1">
                            <span>Memory</span>
                            <span>{dashboardData.system_health.memory_usage.toFixed(1)}%</span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div
                              className={`h-2 rounded-full ${
                                dashboardData.system_health.memory_usage >= 80 ? 'bg-red-500' :
                                dashboardData.system_health.memory_usage >= 60 ? 'bg-yellow-500' : 'bg-green-500'
                              }`}
                              style={{ width: `${Math.min(dashboardData.system_health.memory_usage, 100)}%` }}
                            />
                          </div>
                        </div>

                        {/* Disk Progress Bar */}
                        <div>
                          <div className="flex justify-between text-sm mb-1">
                            <span>Disk</span>
                            <span>{dashboardData.system_health.disk_usage.toFixed(1)}%</span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div
                              className={`h-2 rounded-full ${
                                dashboardData.system_health.disk_usage >= 80 ? 'bg-red-500' :
                                dashboardData.system_health.disk_usage >= 60 ? 'bg-yellow-500' : 'bg-green-500'
                              }`}
                              style={{ width: `${Math.min(dashboardData.system_health.disk_usage, 100)}%` }}
                            />
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* System Info */}
                    <div className="bg-white dark:bg-gray-700 p-6 rounded-lg border border-gray-200 dark:border-gray-600">
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">System Information</h3>
                      <div className="space-y-3 text-sm">
                        <div className="flex justify-between">
                          <span className="text-gray-600 dark:text-gray-400">Uptime:</span>
                          <span className="font-medium">{formatUptime(dashboardData.system_health.uptime_seconds)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600 dark:text-gray-400">API Latency (P95):</span>
                          <span className="font-medium">{dashboardData.system_health.api_latency_p95.toFixed(0)}ms</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600 dark:text-gray-400">Active Alerts:</span>
                          <span className={`font-medium ${dashboardData.system_health.alerts_count > 0 ? 'text-red-500' : 'text-green-500'}`}>
                            {dashboardData.system_health.alerts_count}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600 dark:text-gray-400">Active Users:</span>
                          <span className="font-medium">{dashboardData.system_health.active_users}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Recent Alerts Preview */}
                  {dashboardData.alerts.length > 0 && (
                    <div className="bg-white dark:bg-gray-700 p-6 rounded-lg border border-gray-200 dark:border-gray-600">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Recent Alerts</h3>
                        <button
                          onClick={() => setSelectedTab('alerts')}
                          className="text-sm text-primary-600 hover:text-primary-700"
                        >
                          View All
                        </button>
                      </div>
                      <div className="space-y-2">
                        {dashboardData.alerts.slice(0, 3).map((alert) => (
                          <div
                            key={alert.id}
                            className={`p-3 rounded-lg border ${getSeverityColor(alert.severity)}`}
                          >
                            <div className="flex items-center justify-between">
                              <div>
                                <p className="font-medium">{alert.message}</p>
                                <p className="text-xs opacity-75">
                                  {new Date(alert.created_at).toLocaleString()}
                                </p>
                              </div>
                              <span className="text-xs px-2 py-1 bg-white dark:bg-gray-800 rounded-full">
                                {alert.severity}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Metrics Tab */}
              {selectedTab === 'metrics' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="bg-white dark:bg-gray-700 p-6 rounded-lg border border-gray-200 dark:border-gray-600">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Average CPU Usage (1h)</h3>
                    <div className="text-3xl font-bold text-blue-500">
                      {dashboardData.recent_metrics.cpu.value.toFixed(1)}%
                    </div>
                    <div className="text-sm text-gray-500">
                      Based on {dashboardData.recent_metrics.cpu.count} data points
                    </div>
                  </div>

                  <div className="bg-white dark:bg-gray-700 p-6 rounded-lg border border-gray-200 dark:border-gray-600">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Average Memory Usage (1h)</h3>
                    <div className="text-3xl font-bold text-green-500">
                      {dashboardData.recent_metrics.memory.value.toFixed(1)}%
                    </div>
                    <div className="text-sm text-gray-500">
                      Based on {dashboardData.recent_metrics.memory.count} data points
                    </div>
                  </div>

                  <div className="bg-white dark:bg-gray-700 p-6 rounded-lg border border-gray-200 dark:border-gray-600">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Average Disk Usage (1h)</h3>
                    <div className="text-3xl font-bold text-orange-500">
                      {dashboardData.recent_metrics.disk.value.toFixed(1)}%
                    </div>
                    <div className="text-sm text-gray-500">
                      Based on {dashboardData.recent_metrics.disk.count} data points
                    </div>
                  </div>

                  <div className="bg-white dark:bg-gray-700 p-6 rounded-lg border border-gray-200 dark:border-gray-600">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">API Latency P95 (1h)</h3>
                    <div className="text-3xl font-bold text-purple-500">
                      {dashboardData.recent_metrics.api_latency.value.toFixed(0)}ms
                    </div>
                    <div className="text-sm text-gray-500">
                      Based on {dashboardData.recent_metrics.api_latency.count} requests
                    </div>
                  </div>
                </div>
              )}

              {/* Alerts Tab */}
              {selectedTab === 'alerts' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                      Active Alerts ({dashboardData.alerts.length})
                    </h3>
                  </div>
                  
                  {dashboardData.alerts.length === 0 ? (
                    <div className="text-center py-12">
                      <HiCheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
                      <p className="text-gray-500 dark:text-gray-400">
                        No active alerts - system is running smoothly!
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {dashboardData.alerts.map((alert) => (
                        <div
                          key={alert.id}
                          className={`p-4 rounded-lg border ${getSeverityColor(alert.severity)}`}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <div className="flex items-center space-x-2 mb-2">
                                <HiExclamationTriangle className="w-4 h-4" />
                                <span className="font-medium">{alert.message}</span>
                                <span className="text-xs px-2 py-1 bg-white dark:bg-gray-800 rounded-full">
                                  {alert.severity}
                                </span>
                              </div>
                              <div className="text-sm opacity-75">
                                <p>Threshold: {alert.threshold} | Current: {alert.current_value.toFixed(2)}</p>
                                <p>Created: {new Date(alert.created_at).toLocaleString()}</p>
                              </div>
                            </div>
                            <button
                              onClick={() => resolveAlert(alert.id)}
                              className="ml-4 px-3 py-1 bg-white dark:bg-gray-800 text-sm rounded hover:bg-gray-50 dark:hover:bg-gray-700"
                            >
                              Resolve
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Insights Tab */}
              {selectedTab === 'insights' && (
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    Performance Insights & Recommendations
                  </h3>
                  
                  {dashboardData.insights.length === 0 ? (
                    <div className="text-center py-12">
                      <HiLightBulb className="w-12 h-12 text-yellow-500 mx-auto mb-4" />
                      <p className="text-gray-500 dark:text-gray-400">
                        No insights available - system is performing optimally!
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {dashboardData.insights.map((insight, index) => (
                        <div
                          key={index}
                          className={`p-4 rounded-lg border ${getSeverityColor(insight.severity)}`}
                        >
                          <div className="flex items-start space-x-3">
                            <HiLightBulb className="w-5 h-5 mt-0.5" />
                            <div className="flex-1">
                              <div className="flex items-center space-x-2 mb-2">
                                <h4 className="font-medium">{insight.title}</h4>
                                <span className="text-xs px-2 py-1 bg-white dark:bg-gray-800 rounded-full">
                                  {insight.severity}
                                </span>
                              </div>
                              <p className="text-sm mb-2 opacity-75">{insight.description}</p>
                              <div className="text-sm">
                                <span className="font-medium">Recommendation: </span>
                                {insight.recommendation}
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};