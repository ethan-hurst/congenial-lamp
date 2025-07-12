/**
 * Main Code Editor Component with tabs, file tree, and Monaco
 */
import React, { useState, useCallback } from 'react';
import { MonacoEditor } from './MonacoEditor';
import { FileTree } from '../FileSystem/FileTree';
import { EditorTabs } from './EditorTabs';
import { Terminal } from '../Terminal/Terminal';
import { OutputPanel } from '../Output/OutputPanel';
import { useEditorStore } from '../../stores/editorStore';
import { useProjectStore } from '../../stores/projectStore';
import { FileNode } from '../../types/fileSystem';
import { ResizablePanel, ResizablePanelGroup, ResizableHandle } from '../Common/Resizable';

interface CodeEditorProps {
  projectId: string;
}

export const CodeEditor: React.FC<CodeEditorProps> = ({ projectId }) => {
  const { tabs, activeTabId, openTab, updateTabContent, markTabClean } = useEditorStore();
  const { currentProject } = useProjectStore();
  
  const [showFileTree, setShowFileTree] = useState(true);
  const [showTerminal, setShowTerminal] = useState(true);
  const [terminalHeight, setTerminalHeight] = useState(200);
  
  const activeTab = tabs.find(tab => tab.id === activeTabId);

  // Handle file selection from tree
  const handleFileSelect = useCallback((file: FileNode) => {
    if (file.type === 'file') {
      // Check if already open
      const existingTab = tabs.find(tab => tab.filePath === file.path);
      
      if (existingTab) {
        useEditorStore.setState({ activeTabId: existingTab.id });
      } else {
        openTab({
          filePath: file.path,
          fileName: file.name,
          content: file.content || '',
          language: getLanguageFromPath(file.path),
        });
      }
    }
  }, [tabs, openTab]);

  // Handle file save
  const handleSave = useCallback(async (content: string) => {
    if (!activeTab) return;
    
    try {
      // Save file via API
      const response = await fetch(`/api/projects/${projectId}/files${activeTab.filePath}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      });
      
      if (response.ok) {
        markTabClean(activeTab.id);
        // Show success notification
      }
    } catch (error) {
      console.error('Failed to save file:', error);
      // Show error notification
    }
  }, [activeTab, projectId, markTabClean]);

  // Handle content change
  const handleContentChange = useCallback((content: string) => {
    if (activeTab) {
      updateTabContent(activeTab.id, content);
    }
  }, [activeTab, updateTabContent]);

  const getLanguageFromPath = (path: string): string => {
    const ext = path.split('.').pop()?.toLowerCase();
    const languageMap: Record<string, string> = {
      js: 'javascript',
      jsx: 'javascript',
      ts: 'typescript',
      tsx: 'typescript',
      py: 'python',
      go: 'go',
      rs: 'rust',
      java: 'java',
      cpp: 'cpp',
      c: 'c',
      cs: 'csharp',
      rb: 'ruby',
      php: 'php',
      html: 'html',
      css: 'css',
      scss: 'scss',
      json: 'json',
      md: 'markdown',
      yaml: 'yaml',
      yml: 'yaml',
      xml: 'xml',
      sql: 'sql',
      sh: 'shell',
      bash: 'shell',
    };
    return languageMap[ext || ''] || 'plaintext';
  };

  return (
    <div className="flex flex-col h-screen bg-background">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border">
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-semibold">{currentProject?.name || 'CodeForge'}</h1>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span>{currentProject?.language}</span>
            {currentProject?.framework && (
              <>
                <span>•</span>
                <span>{currentProject.framework}</span>
              </>
            )}
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowFileTree(!showFileTree)}
            className="p-2 hover:bg-accent rounded"
            title="Toggle File Tree"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
            </svg>
          </button>
          <button
            onClick={() => setShowTerminal(!showTerminal)}
            className="p-2 hover:bg-accent rounded"
            title="Toggle Terminal"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* File tree sidebar */}
        {showFileTree && (
          <div className="w-64 border-r border-border overflow-hidden flex flex-col">
            <div className="p-2 border-b border-border">
              <input
                type="text"
                placeholder="Search files..."
                className="w-full px-2 py-1 text-sm bg-input border border-border rounded"
              />
            </div>
            <div className="flex-1 overflow-auto">
              <FileTree projectId={projectId} onFileSelect={handleFileSelect} />
            </div>
          </div>
        )}

        {/* Editor area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Tabs */}
          <EditorTabs />

          {/* Editor and terminal */}
          <ResizablePanelGroup direction="vertical" className="flex-1">
            <ResizablePanel defaultSize={showTerminal ? 70 : 100}>
              {activeTab ? (
                <MonacoEditor
                  key={activeTab.id}
                  file={{
                    id: activeTab.id,
                    name: activeTab.fileName,
                    path: activeTab.filePath,
                    type: 'file',
                    content: activeTab.content,
                  }}
                  onSave={handleSave}
                  onContentChange={handleContentChange}
                />
              ) : (
                <div className="flex items-center justify-center h-full text-muted-foreground">
                  <div className="text-center">
                    <svg className="w-16 h-16 mx-auto mb-4 text-muted-foreground/50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                    </svg>
                    <p className="text-lg font-medium">No file open</p>
                    <p className="text-sm mt-2">Select a file from the explorer to start coding</p>
                  </div>
                </div>
              )}
            </ResizablePanel>

            {showTerminal && (
              <>
                <ResizableHandle />
                <ResizablePanel defaultSize={30} minSize={20}>
                  <div className="h-full flex flex-col bg-background">
                    <div className="flex border-t border-b border-border">
                      <button className="px-4 py-1.5 text-sm border-b-2 border-primary">
                        Terminal
                      </button>
                      <button className="px-4 py-1.5 text-sm text-muted-foreground hover:text-foreground">
                        Output
                      </button>
                      <button className="px-4 py-1.5 text-sm text-muted-foreground hover:text-foreground">
                        Problems
                      </button>
                      <button className="px-4 py-1.5 text-sm text-muted-foreground hover:text-foreground">
                        Debug Console
                      </button>
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <Terminal projectId={projectId} />
                    </div>
                  </div>
                </ResizablePanel>
              </>
            )}
          </ResizablePanelGroup>
        </div>
      </div>
    </div>
  );
};