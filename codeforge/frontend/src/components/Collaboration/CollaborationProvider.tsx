/**
 * Real-time Collaboration Provider
 */
import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import { api } from '../../services/api';
import { useProjectStore } from '../../stores/projectStore';

interface Operation {
  id: string;
  type: 'insert' | 'delete' | 'retain' | 'cursor_move' | 'selection_change';
  position: number;
  length: number;
  content?: string;
  user_id: string;
  timestamp: string;
  file_path: string;
}

interface UserPresence {
  user_id: string;
  username: string;
  avatar_url?: string;
  cursor_position: number;
  selection_start?: number;
  selection_end?: number;
  current_file?: string;
  color: string;
  last_seen: string;
}

interface CollaborationSession {
  project_id: string;
  users: Record<string, UserPresence>;
  file_versions: Record<string, number>;
  operation_count: number;
  last_activity: string;
}

interface CollaborationContextType {
  isCollaborating: boolean;
  collaborators: Record<string, UserPresence>;
  joinSession: (projectId: string) => Promise<void>;
  leaveSession: () => Promise<void>;
  sendOperation: (operation: Omit<Operation, 'id' | 'user_id' | 'timestamp'>) => Promise<void>;
  updateCursor: (filePath: string, position: number, selection?: { start: number; end: number }) => Promise<void>;
  onOperation: (callback: (operation: Operation) => void) => void;
  onUserJoin: (callback: (user: UserPresence) => void) => void;
  onUserLeave: (callback: (userId: string) => void) => void;
  onCursorUpdate: (callback: (userId: string, cursor: { position: number; selection?: { start: number; end: number }; file: string }) => void) => void;
}

const CollaborationContext = createContext<CollaborationContextType | null>(null);

export const useCollaboration = () => {
  const context = useContext(CollaborationContext);
  if (!context) {
    throw new Error('useCollaboration must be used within a CollaborationProvider');
  }
  return context;
};

interface CollaborationProviderProps {
  children: React.ReactNode;
}

export const CollaborationProvider: React.FC<CollaborationProviderProps> = ({ children }) => {
  const { currentProject } = useProjectStore();
  const [isCollaborating, setIsCollaborating] = useState(false);
  const [collaborators, setCollaborators] = useState<Record<string, UserPresence>>({});
  const [websocket, setWebsocket] = useState<WebSocket | null>(null);
  
  // Event callbacks
  const operationCallbacks = useRef<Set<(operation: Operation) => void>>(new Set());
  const userJoinCallbacks = useRef<Set<(user: UserPresence) => void>>(new Set());
  const userLeaveCallbacks = useRef<Set<(userId: string) => void>>(new Set());
  const cursorUpdateCallbacks = useRef<Set<(userId: string, cursor: any) => void>>(new Set());

  const joinSession = useCallback(async (projectId: string) => {
    try {
      // Join via HTTP first
      const response = await api.joinCollaborationSession(projectId);
      
      if (response.success) {
        setCollaborators(response.users || {});
        setIsCollaborating(true);
        
        // Establish WebSocket connection
        const token = localStorage.getItem('auth_token');
        const wsUrl = `${import.meta.env.VITE_WS_URL || 'ws://localhost:8000'}/api/v1/collaboration/sessions/${projectId}/ws?token=${token}`;
        
        const ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
          console.log('Collaboration WebSocket connected');
          setWebsocket(ws);
        };
        
        ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            handleWebSocketMessage(message);
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };
        
        ws.onclose = () => {
          console.log('Collaboration WebSocket disconnected');
          setWebsocket(null);
        };
        
        ws.onerror = (error) => {
          console.error('Collaboration WebSocket error:', error);
        };
        
        // Send ping every 30 seconds to keep connection alive
        const pingInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          } else {
            clearInterval(pingInterval);
          }
        }, 30000);
      }
    } catch (error) {
      console.error('Failed to join collaboration session:', error);
      throw error;
    }
  }, []);

  const leaveSession = useCallback(async () => {
    try {
      if (currentProject?.id) {
        await api.leaveCollaborationSession(currentProject.id);
      }
      
      if (websocket) {
        websocket.close();
        setWebsocket(null);
      }
      
      setIsCollaborating(false);
      setCollaborators({});
    } catch (error) {
      console.error('Failed to leave collaboration session:', error);
    }
  }, [currentProject?.id, websocket]);

  const sendOperation = useCallback(async (operation: Omit<Operation, 'id' | 'user_id' | 'timestamp'>) => {
    if (!websocket || websocket.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket not connected, cannot send operation');
      return;
    }

    try {
      const message = {
        type: 'operation',
        operation: {
          ...operation,
          timestamp: new Date().toISOString()
        }
      };
      
      websocket.send(JSON.stringify(message));
    } catch (error) {
      console.error('Failed to send operation:', error);
    }
  }, [websocket]);

  const updateCursor = useCallback(async (
    filePath: string, 
    position: number, 
    selection?: { start: number; end: number }
  ) => {
    if (!websocket || websocket.readyState !== WebSocket.OPEN) {
      return;
    }

    try {
      const message = {
        type: 'cursor_update',
        cursor: {
          file_path: filePath,
          position,
          selection_start: selection?.start,
          selection_end: selection?.end
        }
      };
      
      websocket.send(JSON.stringify(message));
    } catch (error) {
      console.error('Failed to update cursor:', error);
    }
  }, [websocket]);

  const handleWebSocketMessage = useCallback((message: any) => {
    switch (message.type) {
      case 'session_joined':
        if (message.session) {
          setCollaborators(message.session.users || {});
        }
        break;
        
      case 'collaboration_operation':
        if (message.operation) {
          const operation = message.operation as Operation;
          
          if (operation.type === 'user_join') {
            // Handle user join
            userJoinCallbacks.current.forEach(callback => {
              // We'd need user details from the server
              callback({
                user_id: operation.user_id,
                username: 'Unknown User',
                color: '#007acc',
                cursor_position: 0,
                last_seen: operation.timestamp
              });
            });
          } else if (operation.type === 'user_leave') {
            // Handle user leave
            setCollaborators(prev => {
              const updated = { ...prev };
              delete updated[operation.user_id];
              return updated;
            });
            
            userLeaveCallbacks.current.forEach(callback => {
              callback(operation.user_id);
            });
          } else if (operation.type === 'cursor_move') {
            // Handle cursor update
            cursorUpdateCallbacks.current.forEach(callback => {
              callback(operation.user_id, {
                position: operation.position,
                file: operation.file_path
              });
            });
          } else {
            // Handle regular operations
            operationCallbacks.current.forEach(callback => {
              callback(operation);
            });
          }
        }
        break;
        
      case 'pong':
        // Handle ping response
        break;
        
      case 'error':
        console.error('Collaboration error:', message.message);
        break;
        
      default:
        console.log('Unknown message type:', message.type);
    }
  }, []);

  // Event subscription methods
  const onOperation = useCallback((callback: (operation: Operation) => void) => {
    operationCallbacks.current.add(callback);
    return () => operationCallbacks.current.delete(callback);
  }, []);

  const onUserJoin = useCallback((callback: (user: UserPresence) => void) => {
    userJoinCallbacks.current.add(callback);
    return () => userJoinCallbacks.current.delete(callback);
  }, []);

  const onUserLeave = useCallback((callback: (userId: string) => void) => {
    userLeaveCallbacks.current.add(callback);
    return () => userLeaveCallbacks.current.delete(callback);
  }, []);

  const onCursorUpdate = useCallback((callback: (userId: string, cursor: any) => void) => {
    cursorUpdateCallbacks.current.add(callback);
    return () => cursorUpdateCallbacks.current.delete(callback);
  }, []);

  // Auto-join collaboration when project changes
  useEffect(() => {
    if (currentProject?.id && !isCollaborating) {
      joinSession(currentProject.id).catch(console.error);
    }
    
    return () => {
      if (isCollaborating) {
        leaveSession().catch(console.error);
      }
    };
  }, [currentProject?.id]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (websocket) {
        websocket.close();
      }
    };
  }, [websocket]);

  const contextValue: CollaborationContextType = {
    isCollaborating,
    collaborators,
    joinSession,
    leaveSession,
    sendOperation,
    updateCursor,
    onOperation,
    onUserJoin,
    onUserLeave,
    onCursorUpdate,
  };

  return (
    <CollaborationContext.Provider value={contextValue}>
      {children}
    </CollaborationContext.Provider>
  );
};