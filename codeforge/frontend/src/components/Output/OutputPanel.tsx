/**
 * Output Panel Component - Shows build output, logs, etc.
 */
import React from 'react';

interface OutputPanelProps {
  projectId: string;
}

export const OutputPanel: React.FC<OutputPanelProps> = ({ projectId }) => {
  return (
    <div className="h-full p-4 font-mono text-sm">
      <div className="text-muted-foreground">
        <p>Build output will appear here...</p>
      </div>
    </div>
  );
};