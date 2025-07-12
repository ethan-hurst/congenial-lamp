/**
 * Terminal Component - WebSocket-based terminal emulator
 */
import React, { useEffect, useRef } from 'react';
import { Terminal as XTerm } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import { WebLinksAddon } from 'xterm-addon-web-links';
import 'xterm/css/xterm.css';

interface TerminalProps {
  projectId: string;
}

export const Terminal: React.FC<TerminalProps> = ({ projectId }) => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<XTerm | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

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
    });

    // Add addons
    const fitAddon = new FitAddon();
    const webLinksAddon = new WebLinksAddon();
    
    term.loadAddon(fitAddon);
    term.loadAddon(webLinksAddon);

    // Open terminal in DOM
    term.open(terminalRef.current);
    fitAddon.fit();

    // Store refs
    xtermRef.current = term;
    fitAddonRef.current = fitAddon;

    // Show welcome message
    term.writeln('Welcome to CodeForge Terminal! 🚀');
    term.writeln('');
    term.writeln('Connecting to container...');
    
    // Connect to WebSocket
    connectToWebSocket(term);

    // Handle resize
    const handleResize = () => {
      fitAddon.fit();
    };
    window.addEventListener('resize', handleResize);

    // Handle terminal input
    term.onData((data) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'terminal_input',
          data,
        }));
      }
    });

    return () => {
      window.removeEventListener('resize', handleResize);
      wsRef.current?.close();
      term.dispose();
    };
  }, [projectId]);

  const connectToWebSocket = (term: XTerm) => {
    // In production, this would connect to the actual WebSocket server
    const ws = new WebSocket(`ws://localhost:8765/terminal/${projectId}`);

    ws.onopen = () => {
      term.writeln('\rConnected to container! ✓');
      term.writeln('');
      term.write('$ ');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'terminal_output') {
        term.write(data.data);
      }
    };

    ws.onerror = (error) => {
      term.writeln('\r\nConnection error! Please try again.');
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      term.writeln('\r\nDisconnected from container.');
    };

    wsRef.current = ws;
  };

  return (
    <div className="h-full bg-[#1e1e1e] p-2">
      <div ref={terminalRef} className="h-full" />
    </div>
  );
};