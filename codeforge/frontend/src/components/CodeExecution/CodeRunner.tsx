/**
 * Code Runner Component - Executes code via WebSocket
 */
import React, { useState, useEffect } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useAuth } from '@/hooks/useAuth';

interface CodeRunnerProps {
  containerId: string;
  code: string;
  language: string;
  filename?: string;
  onOutput?: (output: string, type: 'stdout' | 'stderr') => void;
  onComplete?: (exitCode: number) => void;
}

export const CodeRunner: React.FC<CodeRunnerProps> = ({
  containerId,
  code,
  language,
  filename,
  onOutput,
  onComplete,
}) => {
  const { token } = useAuth();
  const [isRunning, setIsRunning] = useState(false);
  const [output, setOutput] = useState<Array<{ type: string; data: string }>>([]);

  const { isConnected, lastMessage, send } = useWebSocket({
    url: `${process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'}/api/v1/ws/execute/${containerId}`,
    token,
    reconnect: false,
  });

  useEffect(() => {
    if (!lastMessage) return;

    switch (lastMessage.type) {
      case 'stdout':
        setOutput(prev => [...prev, { type: 'stdout', data: lastMessage.data }]);
        onOutput?.(lastMessage.data, 'stdout');
        break;
        
      case 'stderr':
        setOutput(prev => [...prev, { type: 'stderr', data: lastMessage.data }]);
        onOutput?.(lastMessage.data, 'stderr');
        break;
        
      case 'exit':
        setIsRunning(false);
        onComplete?.(lastMessage.data);
        break;
        
      case 'error':
        setIsRunning(false);
        setOutput(prev => [...prev, { type: 'error', data: lastMessage.data }]);
        break;
    }
  }, [lastMessage, onOutput, onComplete]);

  const runCode = () => {
    if (!isConnected || isRunning) return;

    setIsRunning(true);
    setOutput([]);

    send({
      type: 'execute',
      code,
      language,
      filename,
    });
  };

  const stopExecution = () => {
    if (!isConnected) return;

    send({
      type: 'stop',
    });
    
    setIsRunning(false);
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-3 border-b border-gray-700">
        <h3 className="text-sm font-medium text-gray-300">Output</h3>
        <div className="flex items-center space-x-2">
          {isRunning ? (
            <button
              onClick={stopExecution}
              className="px-3 py-1 text-sm text-white bg-red-600 rounded hover:bg-red-700"
            >
              Stop
            </button>
          ) : (
            <button
              onClick={runCode}
              disabled={!isConnected}
              className="px-3 py-1 text-sm text-white bg-green-600 rounded hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed"
            >
              Run
            </button>
          )}
        </div>
      </div>
      
      <div className="flex-1 p-3 overflow-auto bg-gray-900 font-mono text-sm">
        {output.length === 0 && !isRunning && (
          <div className="text-gray-500">Click "Run" to execute your code...</div>
        )}
        
        {output.map((item, index) => (
          <div
            key={index}
            className={`whitespace-pre-wrap ${
              item.type === 'stderr' || item.type === 'error'
                ? 'text-red-400'
                : 'text-gray-300'
            }`}
          >
            {item.data}
          </div>
        ))}
        
        {isRunning && (
          <div className="inline-block animate-pulse">
            <span className="text-gray-500">Running...</span>
          </div>
        )}
      </div>
    </div>
  );
};