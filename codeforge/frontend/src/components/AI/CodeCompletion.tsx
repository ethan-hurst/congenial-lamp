/**
 * AI Code Completion Integration
 */
import React, { useCallback, useEffect, useRef } from 'react';
import * as monaco from 'monaco-editor';
import { HiLightningBolt, HiCode } from 'react-icons/hi';

import { api } from '../../services/api';
import { useProjectStore } from '../../stores/projectStore';

interface CompletionItem {
  code: string;
  description: string;
  confidence: number;
}

interface CodeCompletionProps {
  editor: monaco.editor.IStandaloneCodeEditor;
  language: string;
  filePath: string;
}

export const CodeCompletion: React.FC<CodeCompletionProps> = ({
  editor,
  language,
  filePath,
}) => {
  const { currentProject } = useProjectStore();
  const completionProviderRef = useRef<monaco.IDisposable | null>(null);
  const isRequestingRef = useRef(false);

  const getAICompletions = useCallback(
    async (
      model: monaco.editor.ITextModel,
      position: monaco.Position
    ): Promise<monaco.languages.CompletionItem[]> => {
      if (isRequestingRef.current) return [];

      try {
        isRequestingRef.current = true;

        const content = model.getValue();
        const offset = model.getOffsetAt(position);

        const response = await api.getAICompletion({
          file_path: filePath,
          content,
          language,
          cursor_position: offset,
          max_suggestions: 3,
        });

        if (!response.suggestions) return [];

        return response.suggestions.map((item: CompletionItem, index: number) => ({
          label: {
            label: item.description,
            detail: `AI Suggestion ${index + 1}`,
            description: `Confidence: ${Math.round(item.confidence * 100)}%`,
          },
          kind: monaco.languages.CompletionItemKind.Snippet,
          insertText: item.code,
          insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
          range: new monaco.Range(
            position.lineNumber,
            position.column,
            position.lineNumber,
            position.column
          ),
          sortText: `0${index}`, // Prioritize AI suggestions
          detail: 'CodeForge AI',
          documentation: {
            value: `**AI Generated Code**\n\nConfidence: ${Math.round(item.confidence * 100)}%\n\n\`\`\`${language}\n${item.code}\n\`\`\``,
            isTrusted: true,
          },
          command: {
            id: 'ai.completion.selected',
            title: 'AI Completion Selected',
            arguments: [item],
          },
        }));
      } catch (error) {
        console.error('AI completion error:', error);
        return [];
      } finally {
        isRequestingRef.current = false;
      }
    },
    [filePath, language]
  );

  const setupCompletionProvider = useCallback(() => {
    if (completionProviderRef.current) {
      completionProviderRef.current.dispose();
    }

    completionProviderRef.current = monaco.languages.registerCompletionItemProvider(
      language,
      {
        triggerCharacters: ['.', '(', '[', '{', ' ', '\n'],
        provideCompletionItems: async (model, position, context) => {
          // Only provide AI completions for specific triggers or manual invocation
          if (
            context.triggerKind === monaco.languages.CompletionTriggerKind.TriggerCharacter ||
            context.triggerKind === monaco.languages.CompletionTriggerKind.Invoke
          ) {
            const aiCompletions = await getAICompletions(model, position);
            
            return {
              suggestions: aiCompletions,
            };
          }

          return { suggestions: [] };
        },
      }
    );
  }, [language, getAICompletions]);

  // Setup completion provider when component mounts or language changes
  useEffect(() => {
    setupCompletionProvider();

    // Cleanup on unmount
    return () => {
      if (completionProviderRef.current) {
        completionProviderRef.current.dispose();
      }
    };
  }, [setupCompletionProvider]);

  // Register command for completion selection analytics
  useEffect(() => {
    const commandDisposable = editor.addCommand(
      monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyI,
      () => {
        // Trigger AI completion manually
        editor.trigger('ai', 'editor.action.triggerSuggest', {});
      }
    );

    return () => {
      commandDisposable?.dispose();
    };
  }, [editor]);

  return null; // This component doesn't render anything visible
};

/**
 * AI Code Actions Provider
 */
export const useAICodeActions = (
  editor: monaco.editor.IStandaloneCodeEditor,
  language: string,
  filePath: string
) => {
  useEffect(() => {
    const provider = monaco.languages.registerCodeActionProvider(language, {
      provideCodeActions: (model, range, context) => {
        const actions: monaco.languages.CodeAction[] = [];

        // AI Explain Code Action
        if (!range.isEmpty()) {
          actions.push({
            title: '🤖 Explain with AI',
            kind: 'quickfix',
            command: {
              id: 'ai.explain.selection',
              title: 'Explain Selection with AI',
              arguments: [model, range],
            },
          });
        }

        // AI Fix Code Action
        if (context.markers?.length > 0) {
          actions.push({
            title: '🤖 Fix with AI',
            kind: 'quickfix',
            command: {
              id: 'ai.fix.selection',
              title: 'Fix with AI',
              arguments: [model, range, context.markers],
            },
          });
        }

        // AI Refactor Code Action
        if (!range.isEmpty()) {
          actions.push({
            title: '🤖 Refactor with AI',
            kind: 'refactor',
            command: {
              id: 'ai.refactor.selection',
              title: 'Refactor with AI',
              arguments: [model, range],
            },
          });
        }

        return {
          actions,
          dispose: () => {},
        };
      },
    });

    // Register command handlers
    const explainCommand = editor.addCommand(
      'ai.explain.selection',
      async (model: monaco.editor.ITextModel, range: monaco.Range) => {
        const selectedText = model.getValueInRange(range);
        // This would open the AI chat with an explanation request
        console.log('Explain:', selectedText);
      }
    );

    const fixCommand = editor.addCommand(
      'ai.fix.selection',
      async (
        model: monaco.editor.ITextModel,
        range: monaco.Range,
        markers: monaco.editor.IMarker[]
      ) => {
        const selectedText = model.getValueInRange(range);
        const errorMessage = markers[0]?.message || '';
        // This would call the AI fix endpoint
        console.log('Fix:', selectedText, errorMessage);
      }
    );

    const refactorCommand = editor.addCommand(
      'ai.refactor.selection',
      async (model: monaco.editor.ITextModel, range: monaco.Range) => {
        const selectedText = model.getValueInRange(range);
        // This would call the AI refactor endpoint
        console.log('Refactor:', selectedText);
      }
    );

    return () => {
      provider.dispose();
      explainCommand?.dispose();
      fixCommand?.dispose();
      refactorCommand?.dispose();
    };
  }, [editor, language, filePath]);
};