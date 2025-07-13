/**
 * Enhanced Terminal Component with backend WebSocket integration
 */
import React, { useEffect, useRef, useState } from 'react';
import { Terminal as XTerm } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import { WebLinksAddon } from 'xterm-addon-web-links';
import { SearchAddon } from 'xterm-addon-search';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useAuth } from '@/hooks/useAuth';
import 'xterm/css/xterm.css';

interface EnhancedTerminalProps {
  projectId: string;
  containerId: string;
  className?: string;
}

export const EnhancedTerminal: React.FC<EnhancedTerminalProps> = ({ 
  projectId, 
  containerId,
  className = '' 
}) => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<XTerm | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const { token } = useAuth();
  
  const [terminalReady, setTerminalReady] = useState(false);

  // WebSocket connection for terminal
  const { isConnected, lastMessage, send } = useWebSocket({
    url: `${process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'}/api/v1/ws/terminal/${containerId}`,
    token,
    reconnect: true,
  });

  useEffect(() => {
    if (!terminalRef.current) return;

    // Create terminal instance
    const term = new XTerm({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: 'JetBrains Mono, Menlo, Monaco, Consolas, monospace',
      theme: {
        background: '#1e1e1e',
        foreground: '#d4d4d4',
        cursor: '#d4d4d4',
        cursorAccent: '#1e1e1e',
        selection: 'rgba(255, 255, 255, 0.3)',
        black: '#000000',
        red: '#cd3131',
        green: '#0dbc79',
        yellow: '#e5e510',
        blue: '#2472c8',
        magenta: '#bc3fbc',
        cyan: '#11a8cd',
        white: '#e5e5e5',
        brightBlack: '#666666',
        brightRed: '#f14c4c',
        brightGreen: '#23d18b',
        brightYellow: '#f5f543',
        brightBlue: '#3b8eea',
        brightMagenta: '#d670d6',
        brightCyan: '#29b8db',
        brightWhite: '#e5e5e5',
      },
      allowProposedApi: true,
      scrollback: 10000,
      convertEol: true,
    });

    // Add addons
    const fitAddon = new FitAddon();
    const webLinksAddon = new WebLinksAddon();
    const searchAddon = new SearchAddon();
    
    term.loadAddon(fitAddon);
    term.loadAddon(webLinksAddon);
    term.loadAddon(searchAddon);

    // Open terminal in DOM
    term.open(terminalRef.current);
    fitAddon.fit();

    // Store refs
    xtermRef.current = term;
    fitAddonRef.current = fitAddon;

    // Show initial message
    term.writeln('🚀 CodeForge Terminal');
    term.writeln('');
    
    setTerminalReady(true);

    // Handle resize
    const handleResize = () => {
      if (fitAddonRef.current) {
        fitAddonRef.current.fit();
        
        // Send new dimensions to backend
        const { rows, cols } = term;
        send({
          type: 'resize',
          rows,
          cols,
        });
      }
    };
    
    // Use ResizeObserver for better resize detection
    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(terminalRef.current);

    // Handle terminal input
    term.onData((data) => {
      send({
        type: 'input',
        data,
      });
    });

    // Handle terminal resize
    term.onResize(({ rows, cols }) => {
      send({
        type: 'resize',
        rows,
        cols,
      });
    });

    return () => {
      resizeObserver.disconnect();
      term.dispose();
    };
  }, []);

  // Handle WebSocket messages
  useEffect(() => {
    if (!lastMessage || !xtermRef.current) return;

    const term = xtermRef.current;

    switch (lastMessage.type) {
      case 'output':
        term.write(lastMessage.data);
        break;
        
      case 'clear':
        term.clear();
        break;
        
      case 'error':
        term.writeln(`\r\n\x1b[31mError: ${lastMessage.data}\x1b[0m`);
        break;
        
      default:
        console.log('Unknown message type:', lastMessage.type);
    }
  }, [lastMessage]);

  // Handle connection status
  useEffect(() => {
    if (!xtermRef.current || !terminalReady) return;

    const term = xtermRef.current;

    if (isConnected) {
      term.writeln('\x1b[32m✓ Connected to container\x1b[0m');
      term.writeln('');
    } else {
      term.writeln('\r\n\x1b[33m⚠ Disconnected from container\x1b[0m');
    }
  }, [isConnected, terminalReady]);

  return (
    <div className={`h-full bg-[#1e1e1e] ${className}`}>
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-700">
        <div className="flex items-center space-x-2">
          <span className="text-sm text-gray-400">Terminal</span>
          {isConnected && (
            <span className="inline-block w-2 h-2 bg-green-500 rounded-full" />
          )}
        </div>
        <div className="flex items-center space-x-2">
          <button
            className="p-1 text-gray-400 hover:text-white"
            onClick={() => xtermRef.current?.clear()}
            title="Clear terminal"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>
      <div ref={terminalRef} className="h-[calc(100%-42px)] p-2" />
    </div>
  );
};