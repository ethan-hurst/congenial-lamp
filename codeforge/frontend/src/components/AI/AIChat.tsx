/**
 * AI Chat Component
 */
import React, { useState, useRef, useEffect } from 'react';
import { HiPaperAirplane, HiLightningBolt, HiCode, HiCog, HiX } from 'react-icons/hi';
import { FaRobot } from 'react-icons/fa';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/cjs/styles/prism';

import { api } from '../../services/api';
import { useProjectStore } from '../../stores/projectStore';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
}

interface AIChatProps {
  isOpen: boolean;
  onClose: () => void;
  projectContext?: any;
}

export const AIChat: React.FC<AIChatProps> = ({ isOpen, onClose, projectContext }) => {
  const { currentProject } = useProjectStore();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: `Hello! I'm CodeForge AI, your intelligent coding assistant. I can help you with:

• **Code completion** and suggestions
• **Bug fixes** and debugging
• **Code explanations** and documentation
• **Refactoring** and optimization
• **Feature implementation** from descriptions
• **Code reviews** and best practices

What would you like to work on today?`,
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // Create assistant message for streaming
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        isStreaming: true,
      };

      setMessages(prev => [...prev, assistantMessage]);

      // Send chat request
      const response = await api.getAIChat([
        ...messages.map(m => ({ role: m.role, content: m.content })),
        { role: userMessage.role, content: userMessage.content }
      ]);

      // Update the streaming message with final content
      setMessages(prev =>
        prev.map(msg =>
          msg.id === assistantMessage.id
            ? { ...msg, content: response.content, isStreaming: false }
            : msg
        )
      );
    } catch (error) {
      console.error('Chat error:', error);
      
      // Add error message
      const errorMessage: Message = {
        id: (Date.now() + 2).toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const quickActions = [
    {
      icon: <HiCode className="w-4 h-4" />,
      label: 'Explain this code',
      action: () => setInput('Can you explain how this code works?'),
    },
    {
      icon: <HiLightningBolt className="w-4 h-4" />,
      label: 'Fix bugs',
      action: () => setInput('Help me find and fix bugs in my code'),
    },
    {
      icon: <HiCog className="w-4 h-4" />,
      label: 'Optimize code',
      action: () => setInput('How can I optimize and improve this code?'),
    },
  ];

  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700 flex flex-col z-50">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center space-x-2">
          <FaRobot className="w-6 h-6 text-primary-600 dark:text-primary-400" />
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">CodeForge AI</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {currentProject ? `In ${currentProject.name}` : 'Ready to help'}
            </p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
        >
          <HiX className="w-5 h-5" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-3 py-2 ${
                message.role === 'user'
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
              }`}
            >
              {message.role === 'assistant' ? (
                <div className="prose prose-sm dark:prose-invert max-w-none">
                  <ReactMarkdown
                    components={{
                      code({ node, inline, className, children, ...props }) {
                        const match = /language-(\w+)/.exec(className || '');
                        return !inline && match ? (
                          <SyntaxHighlighter
                            style={vscDarkPlus}
                            language={match[1]}
                            PreTag="div"
                            customStyle={{
                              margin: 0,
                              borderRadius: '0.375rem',
                              fontSize: '0.875rem',
                            }}
                            {...props}
                          >
                            {String(children).replace(/\n$/, '')}
                          </SyntaxHighlighter>
                        ) : (
                          <code className={className} {...props}>
                            {children}
                          </code>
                        );
                      },
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                  {message.isStreaming && (
                    <div className="flex items-center mt-2 text-xs text-gray-500">
                      <div className="animate-pulse">AI is thinking...</div>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-sm">{message.content}</p>
              )}
              <div className="text-xs mt-1 opacity-60">
                {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </div>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Actions */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex flex-wrap gap-2 mb-3">
          {quickActions.map((action, index) => (
            <button
              key={index}
              onClick={action.action}
              className="flex items-center space-x-1 px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition"
            >
              {action.icon}
              <span>{action.label}</span>
            </button>
          ))}
        </div>

        {/* Input */}
        <div className="flex space-x-2">
          <div className="flex-1 relative">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask me anything about your code..."
              className="w-full px-3 py-2 text-sm bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
              rows={2}
              disabled={isLoading}
            />
          </div>
          <button
            onClick={sendMessage}
            disabled={!input.trim() || isLoading}
            className="p-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            {isLoading ? (
              <div className="animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full" />
            ) : (
              <HiPaperAirplane className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
};