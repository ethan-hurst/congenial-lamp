/**
 * Collaborative Cursor Component
 * Shows other users' cursors and selections in the editor
 */
import React, { useEffect, useState, useRef } from 'react';
import * as monaco from 'monaco-editor';

interface CollaborativeCursorProps {
  editor: monaco.editor.IStandaloneCodeEditor;
  userId: string;
  username: string;
  color: string;
  position: number;
  selection?: {
    start: number;
    end: number;
  };
  filePath: string;
  currentFile?: string;
}

export const CollaborativeCursor: React.FC<CollaborativeCursorProps> = ({
  editor,
  userId,
  username,
  color,
  position,
  selection,
  filePath,
  currentFile,
}) => {
  const [decorations, setDecorations] = useState<string[]>([]);
  const [widget, setWidget] = useState<monaco.editor.IContentWidget | null>(null);
  const widgetRef = useRef<HTMLDivElement | null>(null);

  // Only show cursor if user is in the same file
  const isVisible = currentFile === filePath;

  useEffect(() => {
    if (!editor || !isVisible) {
      // Clean up existing decorations and widget
      if (decorations.length > 0) {
        editor.deltaDecorations(decorations, []);
        setDecorations([]);
      }
      if (widget) {
        editor.removeContentWidget(widget);
        setWidget(null);
      }
      return;
    }

    const model = editor.getModel();
    if (!model) return;

    // Convert position to line/column
    const cursorPosition = model.getPositionAt(position);
    
    // Create cursor decoration
    const cursorDecoration: monaco.editor.IModelDeltaDecoration = {
      range: new monaco.Range(
        cursorPosition.lineNumber,
        cursorPosition.column,
        cursorPosition.lineNumber,
        cursorPosition.column
      ),
      options: {
        className: 'collaborative-cursor',
        beforeContentClassName: 'collaborative-cursor-line',
        stickiness: monaco.editor.TrackedRangeStickiness.NeverGrowsWhenTypingAtEdges,
      },
    };

    const decorationsToAdd: monaco.editor.IModelDeltaDecoration[] = [cursorDecoration];

    // Add selection decoration if there's a selection
    if (selection && selection.start !== selection.end) {
      const startPosition = model.getPositionAt(selection.start);
      const endPosition = model.getPositionAt(selection.end);
      
      const selectionDecoration: monaco.editor.IModelDeltaDecoration = {
        range: new monaco.Range(
          startPosition.lineNumber,
          startPosition.column,
          endPosition.lineNumber,
          endPosition.column
        ),
        options: {
          className: 'collaborative-selection',
          stickiness: monaco.editor.TrackedRangeStickiness.NeverGrowsWhenTypingAtEdges,
        },
      };
      
      decorationsToAdd.push(selectionDecoration);
    }

    // Apply decorations
    const newDecorations = editor.deltaDecorations(decorations, decorationsToAdd);
    setDecorations(newDecorations);

    // Create cursor label widget
    const cursorWidget: monaco.editor.IContentWidget = {
      getId: () => `collaborative-cursor-${userId}`,
      getDomNode: () => {
        if (!widgetRef.current) {
          const node = document.createElement('div');
          node.className = 'collaborative-cursor-widget';
          node.innerHTML = `
            <div class="collaborative-cursor-label" style="background-color: ${color};">
              ${username}
            </div>
          `;
          widgetRef.current = node;
        }
        return widgetRef.current;
      },
      getPosition: () => ({
        position: cursorPosition,
        preference: [
          monaco.editor.ContentWidgetPositionPreference.ABOVE,
          monaco.editor.ContentWidgetPositionPreference.BELOW,
        ],
      }),
    };

    // Remove old widget if exists
    if (widget) {
      editor.removeContentWidget(widget);
    }

    // Add new widget
    editor.addContentWidget(cursorWidget);
    setWidget(cursorWidget);

    // Cleanup function
    return () => {
      if (newDecorations.length > 0) {
        editor.deltaDecorations(newDecorations, []);
      }
      if (cursorWidget) {
        editor.removeContentWidget(cursorWidget);
      }
    };
  }, [editor, userId, username, color, position, selection, filePath, currentFile, isVisible]);

  // Add CSS styles for collaborative cursors
  useEffect(() => {
    const styleId = 'collaborative-cursor-styles';
    if (document.getElementById(styleId)) return;

    const style = document.createElement('style');
    style.id = styleId;
    style.textContent = `
      .collaborative-cursor {
        position: relative;
      }
      
      .collaborative-cursor-line::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        width: 2px;
        height: 100%;
        background-color: ${color};
        z-index: 10;
        animation: cursor-blink 1s infinite;
      }
      
      .collaborative-selection {
        background-color: ${color}33 !important;
        border: 1px solid ${color}66;
      }
      
      .collaborative-cursor-widget {
        position: relative;
        z-index: 20;
      }
      
      .collaborative-cursor-label {
        position: relative;
        top: -25px;
        left: -5px;
        padding: 2px 6px;
        border-radius: 3px;
        color: white;
        font-size: 11px;
        font-weight: 500;
        white-space: nowrap;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        pointer-events: none;
        opacity: 0;
        animation: cursor-label-appear 0.3s ease-out forwards;
      }
      
      .collaborative-cursor-label::after {
        content: '';
        position: absolute;
        top: 100%;
        left: 8px;
        width: 0;
        height: 0;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 4px solid ${color};
      }
      
      @keyframes cursor-blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0.3; }
      }
      
      @keyframes cursor-label-appear {
        0% {
          opacity: 0;
          transform: translateY(-5px);
        }
        100% {
          opacity: 1;
          transform: translateY(0);
        }
      }
    `;
    
    document.head.appendChild(style);

    return () => {
      const existingStyle = document.getElementById(styleId);
      if (existingStyle) {
        existingStyle.remove();
      }
    };
  }, [color]);

  return null; // This component doesn't render anything directly
};

// Hook for managing multiple collaborative cursors
export const useCollaborativeCursors = (
  editor: monaco.editor.IStandaloneCodeEditor | null,
  currentFilePath: string
) => {
  const [cursors, setCursors] = useState<Map<string, CollaborativeCursorProps>>(new Map());

  const updateCursor = (
    userId: string,
    username: string,
    color: string,
    position: number,
    filePath: string,
    selection?: { start: number; end: number }
  ) => {
    setCursors(prev => {
      const updated = new Map(prev);
      updated.set(userId, {
        editor: editor!,
        userId,
        username,
        color,
        position,
        selection,
        filePath,
        currentFile: currentFilePath,
      });
      return updated;
    });
  };

  const removeCursor = (userId: string) => {
    setCursors(prev => {
      const updated = new Map(prev);
      updated.delete(userId);
      return updated;
    });
  };

  const clearCursors = () => {
    setCursors(new Map());
  };

  return {
    cursors: Array.from(cursors.values()),
    updateCursor,
    removeCursor,
    clearCursors,
  };
};