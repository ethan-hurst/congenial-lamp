/**
 * Monaco Editor Component for CodeForge
 * Features: Syntax highlighting, IntelliSense, multi-file support, themes
 */
import React, { useRef, useEffect, useState, useCallback } from 'react';
import * as monaco from 'monaco-editor';
import { MonacoBinding } from 'y-monaco';
import { WebsocketProvider } from 'y-websocket';
import * as Y from 'yjs';
import { useEditorStore } from '../../stores/editorStore';
import { useProjectStore } from '../../stores/projectStore';
import { useThemeStore } from '../../stores/themeStore';
import { FileNode } from '../../types/fileSystem';
import { debounce } from '../../utils/debounce';

interface MonacoEditorProps {
  file: FileNode;
  onSave?: (content: string) => void;
  onContentChange?: (content: string) => void;
  readOnly?: boolean;
  height?: string;
  showMinimap?: boolean;
}

export const MonacoEditor: React.FC<MonacoEditorProps> = ({
  file,
  onSave,
  onContentChange,
  readOnly = false,
  height = '100%',
  showMinimap = true,
}) => {
  const editorRef = useRef<monaco.editor.IStandaloneCodeEditor | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const monacoBindingRef = useRef<MonacoBinding | null>(null);
  const providerRef = useRef<WebsocketProvider | null>(null);
  
  const { theme, fontSize, tabSize, wordWrap } = useEditorStore();
  const { currentProject } = useProjectStore();
  const { isDarkMode } = useThemeStore();
  
  const [isLoading, setIsLoading] = useState(true);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Initialize Monaco editor
  useEffect(() => {
    if (!containerRef.current) return;

    // Configure Monaco environment
    monaco.editor.setTheme(isDarkMode ? 'vs-dark' : 'vs');
    
    // Configure languages
    monaco.languages.typescript.javascriptDefaults.setDiagnosticsOptions({
      noSemanticValidation: false,
      noSyntaxValidation: false,
    });

    monaco.languages.typescript.javascriptDefaults.setCompilerOptions({
      target: monaco.languages.typescript.ScriptTarget.ES2020,
      allowNonTsExtensions: true,
      moduleResolution: monaco.languages.typescript.ModuleResolutionKind.NodeJs,
      module: monaco.languages.typescript.ModuleKind.CommonJS,
      noEmit: true,
      esModuleInterop: true,
      jsx: monaco.languages.typescript.JsxEmit.React,
      allowJs: true,
      typeRoots: ['node_modules/@types'],
    });

    // Create editor instance
    const editor = monaco.editor.create(containerRef.current, {
      value: file.content || '',
      language: getLanguageFromFilePath(file.path),
      theme: isDarkMode ? 'vs-dark' : 'vs',
      readOnly,
      automaticLayout: true,
      fontSize,
      tabSize,
      wordWrap: wordWrap ? 'on' : 'off',
      minimap: {
        enabled: showMinimap,
      },
      scrollBeyondLastLine: false,
      renderWhitespace: 'selection',
      contextmenu: true,
      quickSuggestions: {
        other: true,
        comments: true,
        strings: true,
      },
      parameterHints: {
        enabled: true,
      },
      suggestOnTriggerCharacters: true,
      acceptSuggestionOnEnter: 'smart',
      snippetSuggestions: 'inline',
      showFoldingControls: 'mouseover',
      folding: true,
      foldingStrategy: 'indentation',
      renderLineHighlight: 'all',
      selectOnLineNumbers: true,
      overviewRulerBorder: false,
      scrollbar: {
        verticalScrollbarSize: 10,
        horizontalScrollbarSize: 10,
      },
    });

    editorRef.current = editor;
    setIsLoading(false);

    // Set up real-time collaboration if enabled
    if (currentProject?.collaborationEnabled) {
      setupCollaboration(editor, file.path);
    }

    // Handle content changes
    const changeDisposable = editor.onDidChangeModelContent(
      debounce(() => {
        const content = editor.getValue();
        setHasUnsavedChanges(true);
        onContentChange?.(content);
      }, 500)
    );

    // Handle save shortcut
    const saveDisposable = editor.addCommand(
      monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS,
      () => {
        const content = editor.getValue();
        onSave?.(content);
        setHasUnsavedChanges(false);
      }
    );

    // Set up IntelliSense providers
    setupIntelliSense(file.path);

    return () => {
      changeDisposable.dispose();
      saveDisposable.dispose();
      editor.dispose();
      monacoBindingRef.current?.destroy();
      providerRef.current?.destroy();
    };
  }, [file.path, isDarkMode, readOnly]);

  // Update editor options when settings change
  useEffect(() => {
    if (editorRef.current) {
      editorRef.current.updateOptions({
        fontSize,
        tabSize,
        wordWrap: wordWrap ? 'on' : 'off',
        theme: isDarkMode ? 'vs-dark' : 'vs',
      });
    }
  }, [fontSize, tabSize, wordWrap, isDarkMode]);

  // Update content when file changes
  useEffect(() => {
    if (editorRef.current && file.content !== undefined) {
      const currentValue = editorRef.current.getValue();
      if (currentValue !== file.content) {
        editorRef.current.setValue(file.content);
        setHasUnsavedChanges(false);
      }
    }
  }, [file.content]);

  // Set up real-time collaboration
  const setupCollaboration = useCallback((editor: monaco.editor.IStandaloneCodeEditor, filePath: string) => {
    const ydoc = new Y.Doc();
    const ytext = ydoc.getText('monaco');

    // Connect to WebSocket server for collaboration
    const provider = new WebsocketProvider(
      `ws://localhost:${1234}`, // YJS_PORT from settings
      `codeforge-${currentProject?.id}-${filePath}`,
      ydoc
    );

    provider.on('sync', (isSynced: boolean) => {
      console.log('Collaboration sync status:', isSynced);
    });

    // Bind Yjs to Monaco
    const monacoBinding = new MonacoBinding(
      ytext,
      editor.getModel()!,
      new Set([editor]),
      provider.awareness
    );

    providerRef.current = provider;
    monacoBindingRef.current = monacoBinding;
  }, [currentProject?.id]);

  // Set up IntelliSense and language features
  const setupIntelliSense = useCallback((filePath: string) => {
    const language = getLanguageFromFilePath(filePath);

    // Register completion provider for custom completions
    monaco.languages.registerCompletionItemProvider(language, {
      provideCompletionItems: async (model, position) => {
        // This would connect to the AI service for intelligent completions
        const word = model.getWordUntilPosition(position);
        const range = {
          startLineNumber: position.lineNumber,
          endLineNumber: position.lineNumber,
          startColumn: word.startColumn,
          endColumn: word.endColumn,
        };

        // Mock completions - in production, these would come from AI
        return {
          suggestions: [
            {
              label: 'codeforge.ai',
              kind: monaco.languages.CompletionItemKind.Method,
              insertText: 'codeforge.ai.complete()',
              detail: 'AI-powered code completion',
              documentation: 'Use CodeForge AI to complete your code',
              range,
            },
          ],
        };
      },
    });

    // Register hover provider for documentation
    monaco.languages.registerHoverProvider(language, {
      provideHover: async (model, position) => {
        // This would fetch documentation from language servers
        const word = model.getWordAtPosition(position);
        if (!word) return null;

        return {
          contents: [
            {
              value: `**${word.word}**\n\nAI-powered documentation for ${word.word}`,
            },
          ],
        };
      },
    });

    // Register code action provider for quick fixes
    monaco.languages.registerCodeActionProvider(language, {
      provideCodeActions: async (model, range, context) => {
        const actions: monaco.languages.CodeAction[] = [];

        // Add AI-powered quick fixes
        if (context.markers.length > 0) {
          actions.push({
            title: '✨ Fix with AI',
            kind: 'quickfix',
            diagnostics: context.markers,
            edit: {
              edits: [
                {
                  resource: model.uri,
                  edit: {
                    range: context.markers[0],
                    text: '// AI fix would go here',
                  },
                },
              ],
            },
          });
        }

        return {
          actions,
          dispose: () => {},
        };
      },
    });
  }, []);

  // Get language from file extension
  const getLanguageFromFilePath = (filePath: string): string => {
    const ext = filePath.split('.').pop()?.toLowerCase();
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

  // Handle editor actions
  const formatDocument = useCallback(() => {
    editorRef.current?.getAction('editor.action.formatDocument')?.run();
  }, []);

  const findInFile = useCallback(() => {
    editorRef.current?.getAction('actions.find')?.run();
  }, []);

  const toggleWordWrap = useCallback(() => {
    const newWordWrap = !wordWrap;
    editorRef.current?.updateOptions({ wordWrap: newWordWrap ? 'on' : 'off' });
    useEditorStore.setState({ wordWrap: newWordWrap });
  }, [wordWrap]);

  return (
    <div className="relative w-full" style={{ height }}>
      {/* Editor toolbar */}
      <div className="absolute top-0 right-0 z-10 flex items-center gap-2 p-2 bg-background/80 backdrop-blur-sm rounded-bl-md">
        {hasUnsavedChanges && (
          <span className="text-xs text-orange-500">● Unsaved</span>
        )}
        <button
          onClick={formatDocument}
          className="p-1 hover:bg-accent rounded"
          title="Format Document (Shift+Alt+F)"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16m-7 6h7" />
          </svg>
        </button>
        <button
          onClick={findInFile}
          className="p-1 hover:bg-accent rounded"
          title="Find (Ctrl+F)"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </button>
        <button
          onClick={toggleWordWrap}
          className="p-1 hover:bg-accent rounded"
          title="Toggle Word Wrap"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h8m-8 6h16" />
          </svg>
        </button>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-background/80 backdrop-blur-sm">
          <div className="text-muted-foreground">Loading editor...</div>
        </div>
      )}

      {/* Monaco container */}
      <div ref={containerRef} className="w-full h-full" />
    </div>
  );
};