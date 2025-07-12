/**
 * AI Assistant Panel
 */
import React, { useState, useCallback } from 'react';
import {
  HiChat,
  HiCode,
  HiLightningBolt,
  HiCog,
  HiDocumentText,
  HiBeaker,
  HiSparkles,
  HiChevronRight,
  HiChevronDown,
} from 'react-icons/hi';
import { FaRobot } from 'react-icons/fa';

import { api } from '../../services/api';
import { useProjectStore } from '../../stores/projectStore';
import { AIChat } from './AIChat';

interface AIAction {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  category: 'code' | 'review' | 'help';
  requiresSelection?: boolean;
}

const AI_ACTIONS: AIAction[] = [
  {
    id: 'explain',
    title: 'Explain Code',
    description: 'Get a detailed explanation of selected code',
    icon: <HiCode className="w-4 h-4" />,
    category: 'help',
    requiresSelection: true,
  },
  {
    id: 'review',
    title: 'Code Review',
    description: 'Get AI feedback on code quality and best practices',
    icon: <HiLightningBolt className="w-4 h-4" />,
    category: 'review',
    requiresSelection: true,
  },
  {
    id: 'fix',
    title: 'Fix Bugs',
    description: 'Identify and fix bugs in your code',
    icon: <HiCog className="w-4 h-4" />,
    category: 'code',
    requiresSelection: true,
  },
  {
    id: 'refactor',
    title: 'Refactor',
    description: 'Improve code structure and readability',
    icon: <HiSparkles className="w-4 h-4" />,
    category: 'code',
    requiresSelection: true,
  },
  {
    id: 'tests',
    title: 'Generate Tests',
    description: 'Create unit tests for your code',
    icon: <HiBeaker className="w-4 h-4" />,
    category: 'code',
    requiresSelection: true,
  },
  {
    id: 'docs',
    title: 'Generate Docs',
    description: 'Create documentation and comments',
    icon: <HiDocumentText className="w-4 h-4" />,
    category: 'help',
    requiresSelection: true,
  },
];

interface AIAssistantPanelProps {
  isOpen: boolean;
  onToggle: () => void;
  currentFile?: {
    path: string;
    content: string;
    language: string;
    selection?: {
      start: number;
      end: number;
    };
  };
  onChatOpen: () => void;
}

export const AIAssistantPanel: React.FC<AIAssistantPanelProps> = ({
  isOpen,
  onToggle,
  currentFile,
  onChatOpen,
}) => {
  const { currentProject } = useProjectStore();
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set(['code', 'review', 'help'])
  );
  const [loadingAction, setLoadingAction] = useState<string | null>(null);
  const [results, setResults] = useState<Map<string, any>>(new Map());

  const toggleCategory = useCallback((category: string) => {
    setExpandedCategories(prev => {
      const newSet = new Set(prev);
      if (newSet.has(category)) {
        newSet.delete(category);
      } else {
        newSet.add(category);
      }
      return newSet;
    });
  }, []);

  const executeAction = useCallback(
    async (action: AIAction) => {
      if (!currentFile) {
        alert('Please open a file first');
        return;
      }

      if (action.requiresSelection && !currentFile.selection) {
        alert('Please select some code first');
        return;
      }

      setLoadingAction(action.id);
      setResults(prev => new Map(prev.set(action.id, null)));

      try {
        let response;
        
        switch (action.id) {
          case 'explain':
            response = await api.explainCode({
              file_path: currentFile.path,
              content: currentFile.content,
              language: currentFile.language,
              selection_start: currentFile.selection?.start,
              selection_end: currentFile.selection?.end,
            });
            break;

          case 'review':
            response = await api.reviewCode({
              file_path: currentFile.path,
              content: currentFile.content,
              language: currentFile.language,
              focus_areas: ['bugs', 'performance', 'security', 'style'],
            });
            break;

          case 'fix':
            response = await api.fixBug({
              file_path: currentFile.path,
              content: currentFile.content,
              language: currentFile.language,
              description: 'Fix any bugs or issues in this code',
            });
            break;

          case 'refactor':
            response = await api.refactorCode({
              file_path: currentFile.path,
              content: currentFile.content,
              language: currentFile.language,
              selection_start: currentFile.selection?.start,
              selection_end: currentFile.selection?.end,
              refactor_type: 'improve',
            });
            break;

          case 'tests':
            response = await api.generateTests({
              file_path: currentFile.path,
              content: currentFile.content,
              language: currentFile.language,
              selection_start: currentFile.selection?.start,
              selection_end: currentFile.selection?.end,
            });
            break;

          case 'docs':
            response = await api.generateDocs({
              file_path: currentFile.path,
              content: currentFile.content,
              language: currentFile.language,
              selection_start: currentFile.selection?.start,
              selection_end: currentFile.selection?.end,
            });
            break;

          default:
            throw new Error(`Unknown action: ${action.id}`);
        }

        setResults(prev => new Map(prev.set(action.id, response)));
      } catch (error) {
        console.error(`AI action ${action.id} failed:`, error);
        setResults(prev => new Map(prev.set(action.id, { error: error.message })));
      } finally {
        setLoadingAction(null);
      }
    },
    [currentFile]
  );

  const groupedActions = AI_ACTIONS.reduce((acc, action) => {
    if (!acc[action.category]) {
      acc[action.category] = [];
    }
    acc[action.category].push(action);
    return acc;
  }, {} as Record<string, AIAction[]>);

  const categoryNames = {
    code: 'Code Generation',
    review: 'Code Review',
    help: 'Understanding',
  };

  if (!isOpen) {
    return (
      <button
        onClick={onToggle}
        className="fixed right-4 top-1/2 transform -translate-y-1/2 bg-primary-600 hover:bg-primary-700 text-white p-3 rounded-l-lg shadow-lg transition-all duration-200 z-40"
        title="Open AI Assistant"
      >
        <FaRobot className="w-5 h-5" />
      </button>
    );
  }

  return (
    <div className="fixed inset-y-0 right-0 w-80 bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700 flex flex-col z-40">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center space-x-2">
          <FaRobot className="w-6 h-6 text-primary-600 dark:text-primary-400" />
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">AI Assistant</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {currentProject ? `In ${currentProject.name}` : 'Ready to help'}
            </p>
          </div>
        </div>
        <button
          onClick={onToggle}
          className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
        >
          <HiChevronRight className="w-5 h-5" />
        </button>
      </div>

      {/* Chat Button */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <button
          onClick={onChatOpen}
          className="w-full flex items-center space-x-2 px-3 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition"
        >
          <HiChat className="w-4 h-4" />
          <span>Open AI Chat</span>
        </button>
      </div>

      {/* Actions */}
      <div className="flex-1 overflow-y-auto">
        {Object.entries(groupedActions).map(([category, actions]) => (
          <div key={category} className="border-b border-gray-200 dark:border-gray-700">
            <button
              onClick={() => toggleCategory(category)}
              className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-50 dark:hover:bg-gray-700 transition"
            >
              <h4 className="font-medium text-gray-900 dark:text-white">
                {categoryNames[category as keyof typeof categoryNames]}
              </h4>
              {expandedCategories.has(category) ? (
                <HiChevronDown className="w-4 h-4 text-gray-500" />
              ) : (
                <HiChevronRight className="w-4 h-4 text-gray-500" />
              )}
            </button>

            {expandedCategories.has(category) && (
              <div className="px-4 pb-4 space-y-2">
                {actions.map(action => {
                  const result = results.get(action.id);
                  const isLoading = loadingAction === action.id;
                  const isDisabled = isLoading || (action.requiresSelection && !currentFile?.selection);

                  return (
                    <div key={action.id} className="space-y-2">
                      <button
                        onClick={() => executeAction(action)}
                        disabled={isDisabled}
                        className={`w-full flex items-start space-x-3 p-3 rounded-lg transition ${
                          isDisabled
                            ? 'bg-gray-100 dark:bg-gray-700 text-gray-400 cursor-not-allowed'
                            : 'bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600 text-gray-900 dark:text-white'
                        }`}
                      >
                        <div className="flex-shrink-0 mt-0.5">
                          {isLoading ? (
                            <div className="animate-spin w-4 h-4 border-2 border-primary-600 border-t-transparent rounded-full" />
                          ) : (
                            action.icon
                          )}
                        </div>
                        <div className="flex-1 text-left">
                          <div className="font-medium text-sm">{action.title}</div>
                          <div className="text-xs text-gray-500 dark:text-gray-400">
                            {action.description}
                          </div>
                        </div>
                      </button>

                      {/* Result Display */}
                      {result && (
                        <div className="ml-7 p-3 bg-gray-100 dark:bg-gray-700 rounded-lg">
                          {result.error ? (
                            <div className="text-red-600 dark:text-red-400 text-sm">
                              Error: {result.error}
                            </div>
                          ) : (
                            <div className="text-sm text-gray-700 dark:text-gray-300 max-h-32 overflow-y-auto">
                              {result.content || 'Action completed successfully'}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Status */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-700">
        <div className="text-xs text-gray-500 dark:text-gray-400 text-center">
          {currentFile ? (
            <>
              File: {currentFile.path}
              {currentFile.selection && (
                <div>Selection: {currentFile.selection.end - currentFile.selection.start} chars</div>
              )}
            </>
          ) : (
            'Open a file to use AI features'
          )}
        </div>
      </div>
    </div>
  );
};