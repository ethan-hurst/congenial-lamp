/**
 * Collaboration Indicator Component
 * Shows active collaborators and their status
 */
import React, { useState, useEffect } from 'react';
import {
  HiUsers,
  HiUserCircle,
  HiEye,
  HiPencil,
  HiWifi,
  HiWifiOff,
  HiChevronDown,
  HiChevronUp
} from 'react-icons/hi';

import { useCollaboration } from './CollaborationProvider';

interface CollaborationIndicatorProps {
  className?: string;
}

export const CollaborationIndicator: React.FC<CollaborationIndicatorProps> = ({ className = '' }) => {
  const { isCollaborating, collaborators } = useCollaboration();
  const [isExpanded, setIsExpanded] = useState(false);
  const [recentActivity, setRecentActivity] = useState<Record<string, Date>>({});

  const collaboratorsList = Object.values(collaborators);
  const activeCount = collaboratorsList.length;

  // Track recent activity
  useEffect(() => {
    const cleanup = useCollaboration().onOperation((operation) => {
      setRecentActivity(prev => ({
        ...prev,
        [operation.user_id]: new Date()
      }));
    });

    return cleanup;
  }, []);

  // Get user activity status
  const getUserActivityStatus = (userId: string, lastSeen: string) => {
    const lastSeenDate = new Date(lastSeen);
    const recentActivityDate = recentActivity[userId];
    const latestActivity = recentActivityDate && recentActivityDate > lastSeenDate 
      ? recentActivityDate 
      : lastSeenDate;
    
    const timeDiff = Date.now() - latestActivity.getTime();
    
    if (timeDiff < 10000) return 'active'; // Active in last 10 seconds
    if (timeDiff < 60000) return 'idle'; // Idle in last minute
    return 'away'; // Away
  };

  const getActivityIcon = (status: string, currentFile?: string) => {
    if (currentFile) {
      if (status === 'active') {
        return <HiPencil className="w-3 h-3 text-green-500" />;
      }
      return <HiEye className="w-3 h-3 text-blue-500" />;
    }
    return null;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-500';
      case 'idle': return 'bg-yellow-500';
      case 'away': return 'bg-gray-400';
      default: return 'bg-gray-400';
    }
  };

  if (!isCollaborating) {
    return (
      <div className={`flex items-center space-x-2 px-3 py-1.5 bg-gray-100 dark:bg-gray-800 rounded-lg ${className}`}>
        <HiWifiOff className="w-4 h-4 text-gray-400" />
        <span className="text-sm text-gray-500 dark:text-gray-400">Not connected</span>
      </div>
    );
  }

  return (
    <div className={`relative ${className}`}>
      {/* Main indicator */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center space-x-2 px-3 py-1.5 bg-green-50 dark:bg-green-900/20 hover:bg-green-100 dark:hover:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-lg transition-colors"
      >
        <HiWifi className="w-4 h-4 text-green-600 dark:text-green-400" />
        <HiUsers className="w-4 h-4 text-green-600 dark:text-green-400" />
        <span className="text-sm font-medium text-green-700 dark:text-green-300">
          {activeCount} {activeCount === 1 ? 'collaborator' : 'collaborators'}
        </span>
        
        {/* Avatar stack for quick preview */}
        <div className="flex -space-x-1">
          {collaboratorsList.slice(0, 3).map((user) => (
            <div
              key={user.user_id}
              className="relative w-6 h-6 rounded-full border-2 border-white dark:border-gray-800 overflow-hidden"
              style={{ backgroundColor: user.color }}
              title={user.username}
            >
              {user.avatar_url ? (
                <img
                  src={user.avatar_url}
                  alt={user.username}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-white text-xs font-medium">
                  {user.username.charAt(0).toUpperCase()}
                </div>
              )}
              
              {/* Status indicator */}
              <div
                className={`absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full border border-white dark:border-gray-800 ${getStatusColor(
                  getUserActivityStatus(user.user_id, user.last_seen)
                )}`}
              />
            </div>
          ))}
          
          {activeCount > 3 && (
            <div className="w-6 h-6 rounded-full bg-gray-100 dark:bg-gray-700 border-2 border-white dark:border-gray-800 flex items-center justify-center">
              <span className="text-xs font-medium text-gray-600 dark:text-gray-300">
                +{activeCount - 3}
              </span>
            </div>
          )}
        </div>
        
        {isExpanded ? (
          <HiChevronUp className="w-4 h-4 text-green-600 dark:text-green-400" />
        ) : (
          <HiChevronDown className="w-4 h-4 text-green-600 dark:text-green-400" />
        )}
      </button>

      {/* Expanded collaborator list */}
      {isExpanded && (
        <div className="absolute top-full right-0 mt-2 w-80 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-50">
          <div className="p-4">
            <h3 className="font-semibold text-gray-900 dark:text-white mb-3">
              Active Collaborators ({activeCount})
            </h3>
            
            <div className="space-y-3 max-h-64 overflow-y-auto">
              {collaboratorsList.map((user) => {
                const activityStatus = getUserActivityStatus(user.user_id, user.last_seen);
                const statusColor = getStatusColor(activityStatus);
                
                return (
                  <div key={user.user_id} className="flex items-center space-x-3">
                    {/* Avatar */}
                    <div className="relative">
                      <div
                        className="w-10 h-10 rounded-full border-2 border-gray-200 dark:border-gray-600 overflow-hidden"
                        style={{ backgroundColor: user.color }}
                      >
                        {user.avatar_url ? (
                          <img
                            src={user.avatar_url}
                            alt={user.username}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-white font-semibold">
                            {user.username.charAt(0).toUpperCase()}
                          </div>
                        )}
                      </div>
                      
                      {/* Status indicator */}
                      <div
                        className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-white dark:border-gray-800 ${statusColor}`}
                      />
                    </div>
                    
                    {/* User info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2">
                        <h4 className="text-sm font-medium text-gray-900 dark:text-white truncate">
                          {user.username}
                        </h4>
                        {getActivityIcon(activityStatus, user.current_file)}
                      </div>
                      
                      <div className="flex items-center space-x-2 text-xs text-gray-500 dark:text-gray-400">
                        <span className="capitalize">{activityStatus}</span>
                        {user.current_file && (
                          <>
                            <span>•</span>
                            <span className="truncate">
                              {user.current_file.split('/').pop()}
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                    
                    {/* Color indicator */}
                    <div
                      className="w-3 h-3 rounded-full flex-shrink-0"
                      style={{ backgroundColor: user.color }}
                      title={`${user.username}'s cursor color`}
                    />
                  </div>
                );
              })}
            </div>
            
            {/* Connection status */}
            <div className="mt-4 pt-3 border-t border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                <div className="flex items-center space-x-1">
                  <HiWifi className="w-3 h-3 text-green-500" />
                  <span>Connected</span>
                </div>
                <span>Real-time sync active</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};