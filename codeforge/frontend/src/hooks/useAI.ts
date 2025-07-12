/**
 * AI Hooks for CodeForge
 */
import { useState, useCallback, useRef } from 'react';
import { api } from '../services/api';

export interface AICodeContext {
  filePath: string;
  content: string;
  language: string;
  cursorPosition?: number;
  selectionStart?: number;
  selectionEnd?: number;
}

export interface AIResponse {
  success: boolean;
  content: string;
  suggestions?: any[];
  confidence?: number;
  processingTime?: number;
  creditsConsumed?: number;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: Date;
}

/**
 * Hook for AI code completion
 */
export const useAICompletion = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [lastResponse, setLastResponse] = useState<AIResponse | null>(null);
  const cancelTokenRef = useRef<AbortController | null>(null);

  const getCompletion = useCallback(async (context: AICodeContext, maxSuggestions = 3) => {
    // Cancel previous request if still pending
    if (cancelTokenRef.current) {
      cancelTokenRef.current.abort();
    }

    const cancelToken = new AbortController();
    cancelTokenRef.current = cancelToken;

    setIsLoading(true);
    try {
      const response = await api.getAICompletion({
        file_path: context.filePath,
        content: context.content,
        language: context.language,
        cursor_position: context.cursorPosition,
        selection_start: context.selectionStart,
        selection_end: context.selectionEnd,
        max_suggestions: maxSuggestions,
      });

      if (!cancelToken.signal.aborted) {
        setLastResponse(response);
        return response;
      }
    } catch (error) {
      if (!cancelToken.signal.aborted) {
        console.error('AI completion error:', error);
        throw error;
      }
    } finally {
      if (!cancelToken.signal.aborted) {
        setIsLoading(false);
      }
    }
  }, []);

  const cancelCompletion = useCallback(() => {
    if (cancelTokenRef.current) {
      cancelTokenRef.current.abort();
      setIsLoading(false);
    }
  }, []);

  return {
    getCompletion,
    cancelCompletion,
    isLoading,
    lastResponse,
  };
};

/**
 * Hook for AI code explanation
 */
export const useAIExplanation = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [explanation, setExplanation] = useState<string | null>(null);

  const explainCode = useCallback(async (context: AICodeContext) => {
    setIsLoading(true);
    try {
      const response = await api.explainCode({
        file_path: context.filePath,
        content: context.content,
        language: context.language,
        selection_start: context.selectionStart,
        selection_end: context.selectionEnd,
      });

      setExplanation(response.content);
      return response;
    } catch (error) {
      console.error('AI explanation error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    explainCode,
    explanation,
    isLoading,
  };
};

/**
 * Hook for AI code review
 */
export const useAIReview = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [review, setReview] = useState<AIResponse | null>(null);

  const reviewCode = useCallback(async (context: AICodeContext, focusAreas: string[] = []) => {
    setIsLoading(true);
    try {
      const response = await api.reviewCode({
        file_path: context.filePath,
        content: context.content,
        language: context.language,
        focus_areas: focusAreas.length > 0 ? focusAreas : ['bugs', 'performance', 'security', 'style'],
      });

      setReview(response);
      return response;
    } catch (error) {
      console.error('AI review error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    reviewCode,
    review,
    isLoading,
  };
};

/**
 * Hook for AI bug fixing
 */
export const useAIBugFix = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [fix, setFix] = useState<AIResponse | null>(null);

  const fixBug = useCallback(async (
    context: AICodeContext,
    description: string,
    errorMessage?: string
  ) => {
    setIsLoading(true);
    try {
      const response = await api.fixBug({
        file_path: context.filePath,
        content: context.content,
        language: context.language,
        description,
        error_message: errorMessage,
      });

      setFix(response);
      return response;
    } catch (error) {
      console.error('AI bug fix error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    fixBug,
    fix,
    isLoading,
  };
};

/**
 * Hook for AI code refactoring
 */
export const useAIRefactor = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [refactor, setRefactor] = useState<AIResponse | null>(null);

  const refactorCode = useCallback(async (
    context: AICodeContext,
    refactorType = 'improve'
  ) => {
    setIsLoading(true);
    try {
      const response = await api.refactorCode({
        file_path: context.filePath,
        content: context.content,
        language: context.language,
        selection_start: context.selectionStart,
        selection_end: context.selectionEnd,
        refactor_type: refactorType,
      });

      setRefactor(response);
      return response;
    } catch (error) {
      console.error('AI refactor error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    refactorCode,
    refactor,
    isLoading,
  };
};

/**
 * Hook for AI test generation
 */
export const useAITestGeneration = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [tests, setTests] = useState<AIResponse | null>(null);

  const generateTests = useCallback(async (context: AICodeContext) => {
    setIsLoading(true);
    try {
      const response = await api.generateTests({
        file_path: context.filePath,
        content: context.content,
        language: context.language,
        selection_start: context.selectionStart,
        selection_end: context.selectionEnd,
      });

      setTests(response);
      return response;
    } catch (error) {
      console.error('AI test generation error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    generateTests,
    tests,
    isLoading,
  };
};

/**
 * Hook for AI documentation generation
 */
export const useAIDocumentation = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [docs, setDocs] = useState<AIResponse | null>(null);

  const generateDocs = useCallback(async (context: AICodeContext) => {
    setIsLoading(true);
    try {
      const response = await api.generateDocs({
        file_path: context.filePath,
        content: context.content,
        language: context.language,
        selection_start: context.selectionStart,
        selection_end: context.selectionEnd,
      });

      setDocs(response);
      return response;
    } catch (error) {
      console.error('AI docs generation error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    generateDocs,
    docs,
    isLoading,
  };
};

/**
 * Hook for AI chat
 */
export const useAIChat = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  const sendMessage = useCallback(async (
    message: string,
    projectContext?: any
  ) => {
    const userMessage: ChatMessage = {
      role: 'user',
      content: message,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await api.getAIChat([
        ...messages,
        userMessage,
      ].map(m => ({ role: m.role, content: m.content })));

      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.content,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, assistantMessage]);
      return response;
    } catch (error) {
      console.error('AI chat error:', error);
      
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, errorMessage]);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [messages]);

  const clearChat = useCallback(() => {
    setMessages([]);
  }, []);

  return {
    sendMessage,
    clearChat,
    messages,
    isLoading,
  };
};

/**
 * Hook for AI feature implementation
 */
export const useAIFeatureImplementation = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [implementation, setImplementation] = useState<any | null>(null);

  const implementFeature = useCallback(async (
    description: string,
    requirements: string[] = [],
    projectContext: any,
    language = 'python',
    framework?: string
  ) => {
    setIsLoading(true);
    try {
      const response = await api.implementFeature({
        description,
        requirements,
        project_context: projectContext,
        language,
        framework,
      });

      setImplementation(response);
      return response;
    } catch (error) {
      console.error('AI feature implementation error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    implementFeature,
    implementation,
    isLoading,
  };
};

/**
 * Hook for AI providers information
 */
export const useAIProviders = () => {
  const [providers, setProviders] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchProviders = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await api.getAIProviders();
      setProviders(response.providers);
      return response;
    } catch (error) {
      console.error('AI providers error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    fetchProviders,
    providers,
    isLoading,
  };
};