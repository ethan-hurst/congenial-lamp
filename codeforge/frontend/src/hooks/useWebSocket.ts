/**
 * WebSocket hook for managing WebSocket connections
 */
import { useEffect, useRef, useState, useCallback } from 'react';

interface WebSocketOptions {
  url: string;
  token?: string;
  reconnect?: boolean;
  reconnectInterval?: number;
  reconnectAttempts?: number;
}

interface WebSocketState {
  isConnected: boolean;
  lastMessage: any;
  error: Error | null;
}

export const useWebSocket = (options: WebSocketOptions) => {
  const {
    url,
    token,
    reconnect = true,
    reconnectInterval = 3000,
    reconnectAttempts = 5,
  } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCount = useRef(0);
  const reconnectTimeout = useRef<NodeJS.Timeout>();

  const [state, setState] = useState<WebSocketState>({
    isConnected: false,
    lastMessage: null,
    error: null,
  });

  const connect = useCallback(() => {
    try {
      // Add token to URL if provided
      const wsUrl = token ? `${url}?token=${encodeURIComponent(token)}` : url;
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        console.log('WebSocket connected');
        setState(prev => ({ ...prev, isConnected: true, error: null }));
        reconnectCount.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setState(prev => ({ ...prev, lastMessage: data }));
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setState(prev => ({ ...prev, error: new Error('WebSocket error') }));
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setState(prev => ({ ...prev, isConnected: false }));
        wsRef.current = null;

        // Attempt reconnection
        if (reconnect && reconnectCount.current < reconnectAttempts) {
          reconnectCount.current++;
          console.log(`Reconnecting... (${reconnectCount.current}/${reconnectAttempts})`);
          
          reconnectTimeout.current = setTimeout(() => {
            connect();
          }, reconnectInterval);
        }
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      setState(prev => ({ ...prev, error: error as Error }));
    }
  }, [url, token, reconnect, reconnectInterval, reconnectAttempts]);

  const disconnect = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
    }
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const send = useCallback((data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    } else {
      console.error('WebSocket is not connected');
    }
  }, []);

  useEffect(() => {
    connect();
    
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected: state.isConnected,
    lastMessage: state.lastMessage,
    error: state.error,
    send,
    disconnect,
    reconnect: connect,
  };
};