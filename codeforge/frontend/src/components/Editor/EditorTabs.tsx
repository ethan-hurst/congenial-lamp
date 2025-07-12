/**
 * Editor Tabs Component
 */
import React from 'react';
import { HiX as X } from 'react-icons/hi';
import { useEditorStore } from '../../stores/editorStore';
import clsx from 'clsx';

export const EditorTabs: React.FC = () => {
  const { tabs, activeTabId, setActiveTab, closeTab } = useEditorStore();

  if (tabs.length === 0) {
    return null;
  }

  const getFileIcon = (fileName: string): string => {
    const ext = fileName.split('.').pop()?.toLowerCase();
    const iconMap: Record<string, string> = {
      js: '📄',
      jsx: '⚛️',
      ts: '📘',
      tsx: '⚛️',
      py: '🐍',
      go: '🐹',
      rs: '🦀',
      java: '☕',
      cpp: '📝',
      c: '📝',
      cs: '📝',
      rb: '💎',
      php: '🐘',
      html: '🌐',
      css: '🎨',
      scss: '🎨',
      json: '📋',
      md: '📝',
      yaml: '📋',
      yml: '📋',
      xml: '📋',
      sql: '🗃️',
      sh: '🖥️',
      bash: '🖥️',
    };
    return iconMap[ext || ''] || '📄';
  };

  return (
    <div className="flex items-center bg-background border-b border-border overflow-x-auto">
      <div className="flex">
        {tabs.map((tab) => (
          <div
            key={tab.id}
            className={clsx(
              'group flex items-center gap-2 px-3 py-1.5 border-r border-border cursor-pointer transition-colors',
              {
                'bg-accent text-accent-foreground': tab.id === activeTabId,
                'hover:bg-accent/50': tab.id !== activeTabId,
              }
            )}
            onClick={() => setActiveTab(tab.id)}
          >
            <span className="text-sm">{getFileIcon(tab.fileName)}</span>
            <span className="text-sm whitespace-nowrap">
              {tab.fileName}
              {tab.isDirty && <span className="ml-1 text-orange-500">●</span>}
            </span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                closeTab(tab.id);
              }}
              className="opacity-0 group-hover:opacity-100 hover:bg-accent-foreground/10 rounded p-0.5 transition-opacity"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};