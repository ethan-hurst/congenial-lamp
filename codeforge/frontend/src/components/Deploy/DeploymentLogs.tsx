/**
 * Deployment Logs Component
 */
import React, { useState, useEffect, useRef } from 'react';
import {
  HiX,
  HiArrowPath,
  HiDocumentText,
  HiExclamationTriangle,
  HiInformationCircle,
  HiCheckCircle,
  HiClock
} from 'react-icons/hi2';
import { api } from '../../services/api';

interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
  source: string;
}

interface DeploymentLogsProps {
  deploymentId: string;
  isOpen: boolean;
  onClose: () => void;
}

export const DeploymentLogs: React.FC<DeploymentLogsProps> = ({
  deploymentId,
  isOpen,
  onClose
}) => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const [filterLevel, setFilterLevel] = useState<string>('all');
  const [filterSource, setFilterSource] = useState<string>('all');
  
  const logsEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Load initial logs
  const loadLogs = async () => {
    try {
      setIsLoading(true);
      const response = await api.getDeploymentLogs(deploymentId);
      setLogs(response.logs);
    } catch (error) {
      console.error('Failed to load logs:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Start streaming logs
  const startStreaming = () => {
    if (wsRef.current) return;

    const wsUrl = `ws://localhost:8000/api/v1/deploy/deployments/${deploymentId}/logs/stream`;
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      setIsStreaming(true);
    };
    
    ws.onmessage = (event) => {
      try {
        const logEntry = JSON.parse(event.data);
        
        if (logEntry.type === 'status_update') {
          // Handle deployment completion
          setIsStreaming(false);
          return;
        }
        
        if (logEntry.type === 'error') {
          console.error('Stream error:', logEntry.message);
          setIsStreaming(false);
          return;
        }
        
        // Add new log entry
        setLogs(prev => [...prev, logEntry]);
      } catch (error) {
        console.error('Failed to parse log entry:', error);
      }
    };
    
    ws.onclose = () => {
      setIsStreaming(false);
      wsRef.current = null;
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setIsStreaming(false);
    };
    
    wsRef.current = ws;
  };

  // Stop streaming logs
  const stopStreaming = () => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsStreaming(false);
  };

  // Get log level icon and color
  const getLogLevelDisplay = (level: string) => {
    switch (level.toLowerCase()) {
      case 'error':
        return { icon: HiExclamationTriangle, color: 'text-red-500' };
      case 'warning':
        return { icon: HiExclamationTriangle, color: 'text-yellow-500' };
      case 'info':
        return { icon: HiInformationCircle, color: 'text-blue-500' };
      case 'success':
        return { icon: HiCheckCircle, color: 'text-green-500' };
      default:
        return { icon: HiInformationCircle, color: 'text-gray-500' };
    }
  };

  // Filter logs
  const filteredLogs = logs.filter(log => {
    if (filterLevel !== 'all' && log.level !== filterLevel) return false;
    if (filterSource !== 'all' && log.source !== filterSource) return false;
    return true;
  });

  // Auto scroll to bottom
  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  // Load logs when modal opens
  useEffect(() => {
    if (isOpen) {
      loadLogs();
      startStreaming();
    } else {
      stopStreaming();
    }
    
    return () => {
      stopStreaming();
    };
  }, [isOpen, deploymentId]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-4xl h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <HiDocumentText className="w-6 h-6 text-primary-600 dark:text-primary-400" />
            <div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                Deployment Logs
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Real-time deployment progress and logs
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            {/* Streaming Status */}
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${isStreaming ? 'bg-green-500' : 'bg-gray-400'}`} />
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {isStreaming ? 'Live' : 'Static'}
              </span>
            </div>
            
            {/* Refresh Button */}
            <button
              onClick={loadLogs}
              disabled={isLoading}
              className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              <HiArrowPath className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
            
            {/* Close Button */}
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              <HiX className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              {/* Level Filter */}
              <div className="flex items-center space-x-2">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Level:
                </label>
                <select
                  value={filterLevel}
                  onChange={(e) => setFilterLevel(e.target.value)}
                  className="text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1 bg-white dark:bg-gray-700"
                >
                  <option value="all">All</option>
                  <option value="error">Error</option>
                  <option value="warning">Warning</option>
                  <option value="info">Info</option>
                </select>
              </div>
              
              {/* Source Filter */}
              <div className="flex items-center space-x-2">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Source:
                </label>
                <select
                  value={filterSource}
                  onChange={(e) => setFilterSource(e.target.value)}
                  className="text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1 bg-white dark:bg-gray-700"
                >
                  <option value="all">All</option>
                  <option value="build">Build</option>
                  <option value="deploy">Deploy</option>
                  <option value="install">Install</option>
                </select>
              </div>
            </div>
            
            {/* Auto-scroll Toggle */}
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
                className="rounded border-gray-300 dark:border-gray-600"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">Auto-scroll</span>
            </label>
          </div>
        </div>

        {/* Logs Content */}
        <div className="flex-1 overflow-auto p-4 bg-gray-900 text-gray-100 font-mono text-sm">
          {isLoading && logs.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="animate-spin w-6 h-6 border-2 border-primary-600 border-t-transparent rounded-full" />
            </div>
          ) : filteredLogs.length === 0 ? (
            <div className="flex items-center justify-center h-full text-gray-500">
              No logs available
            </div>
          ) : (
            <div className="space-y-1">
              {filteredLogs.map((log, index) => {
                const levelDisplay = getLogLevelDisplay(log.level);
                const LevelIcon = levelDisplay.icon;
                
                return (
                  <div
                    key={index}
                    className="flex items-start space-x-3 py-1 hover:bg-gray-800 px-2 rounded"
                  >
                    {/* Timestamp */}
                    <span className="text-gray-500 text-xs whitespace-nowrap">
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </span>
                    
                    {/* Level Icon */}
                    <LevelIcon className={`w-4 h-4 mt-0.5 ${levelDisplay.color}`} />
                    
                    {/* Source */}
                    <span className="text-gray-400 text-xs uppercase tracking-wide whitespace-nowrap min-w-[60px]">
                      {log.source}
                    </span>
                    
                    {/* Message */}
                    <span className="flex-1 break-words">
                      {log.message}
                    </span>
                  </div>
                );
              })}
              <div ref={logsEndRef} />
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50">
          <div className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400">
            <span>
              {filteredLogs.length} of {logs.length} log entries
            </span>
            <span>
              Deployment ID: {deploymentId.slice(0, 8)}...
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};