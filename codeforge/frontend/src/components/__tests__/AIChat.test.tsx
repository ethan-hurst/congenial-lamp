/**
 * Tests for AI Chat Component
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { AIChat } from '../AI/AIChat';
import * as api from '../../services/api';

// Mock the API
vi.mock('../../services/api');
const mockApi = vi.mocked(api);

// Mock the project store
vi.mock('../../stores/projectStore', () => ({
  useProjectStore: () => ({
    currentProject: {
      id: 'test-project',
      name: 'Test Project'
    }
  })
}));

describe('AIChat', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    projectContext: {
      id: 'test-project',
      name: 'Test Project'
    }
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders when open', () => {
    render(<AIChat {...defaultProps} />);
    
    expect(screen.getByText('CodeForge AI')).toBeInTheDocument();
    expect(screen.getByText('In Test Project')).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    render(<AIChat {...defaultProps} isOpen={false} />);
    
    expect(screen.queryByText('CodeForge AI')).not.toBeInTheDocument();
  });

  it('displays initial welcome message', () => {
    render(<AIChat {...defaultProps} />);
    
    expect(screen.getByText(/Hello! I'm CodeForge AI/)).toBeInTheDocument();
    expect(screen.getByText(/Code completion/)).toBeInTheDocument();
    expect(screen.getByText(/Bug fixes/)).toBeInTheDocument();
  });

  it('shows quick action buttons', () => {
    render(<AIChat {...defaultProps} />);
    
    expect(screen.getByText('Explain this code')).toBeInTheDocument();
    expect(screen.getByText('Fix bugs')).toBeInTheDocument();
    expect(screen.getByText('Optimize code')).toBeInTheDocument();
  });

  it('handles quick action clicks', () => {
    render(<AIChat {...defaultProps} />);
    
    const explainButton = screen.getByText('Explain this code');
    fireEvent.click(explainButton);
    
    const textarea = screen.getByPlaceholderText('Ask me anything about your code...');
    expect(textarea).toHaveValue('Can you explain how this code works?');
  });

  it('sends message on button click', async () => {
    mockApi.api.getAIChat.mockResolvedValueOnce({
      content: 'This is an AI response'
    });

    render(<AIChat {...defaultProps} />);
    
    const textarea = screen.getByPlaceholderText('Ask me anything about your code...');
    const sendButton = screen.getByRole('button', { name: /send/i });
    
    fireEvent.change(textarea, { target: { value: 'How do I write a function?' } });
    fireEvent.click(sendButton);
    
    await waitFor(() => {
      expect(mockApi.api.getAIChat).toHaveBeenCalledWith([
        expect.objectContaining({
          role: 'assistant',
          content: expect.stringContaining('Hello! I\'m CodeForge AI')
        }),
        expect.objectContaining({
          role: 'user',
          content: 'How do I write a function?'
        })
      ]);
    });
  });

  it('sends message on Enter key press', async () => {
    mockApi.api.getAIChat.mockResolvedValueOnce({
      content: 'This is an AI response'
    });

    render(<AIChat {...defaultProps} />);
    
    const textarea = screen.getByPlaceholderText('Ask me anything about your code...');
    
    fireEvent.change(textarea, { target: { value: 'Test message' } });
    fireEvent.keyPress(textarea, { key: 'Enter', code: 'Enter' });
    
    await waitFor(() => {
      expect(mockApi.api.getAIChat).toHaveBeenCalled();
    });
  });

  it('does not send message on Shift+Enter', () => {
    render(<AIChat {...defaultProps} />);
    
    const textarea = screen.getByPlaceholderText('Ask me anything about your code...');
    
    fireEvent.change(textarea, { target: { value: 'Test message' } });
    fireEvent.keyPress(textarea, { key: 'Enter', code: 'Enter', shiftKey: true });
    
    expect(mockApi.api.getAIChat).not.toHaveBeenCalled();
  });

  it('displays loading state', async () => {
    // Mock a delayed response
    mockApi.api.getAIChat.mockImplementation(() => 
      new Promise(resolve => setTimeout(() => resolve({ content: 'Response' }), 100))
    );

    render(<AIChat {...defaultProps} />);
    
    const textarea = screen.getByPlaceholderText('Ask me anything about your code...');
    const sendButton = screen.getByRole('button', { name: /send/i });
    
    fireEvent.change(textarea, { target: { value: 'Test message' } });
    fireEvent.click(sendButton);
    
    // Should show loading spinner
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /send/i })).toBeDisabled();
    });
  });

  it('displays AI response', async () => {
    mockApi.api.getAIChat.mockResolvedValueOnce({
      content: 'This is a helpful AI response about functions'
    });

    render(<AIChat {...defaultProps} />);
    
    const textarea = screen.getByPlaceholderText('Ask me anything about your code...');
    
    fireEvent.change(textarea, { target: { value: 'How do I write a function?' } });
    fireEvent.keyPress(textarea, { key: 'Enter', code: 'Enter' });
    
    await waitFor(() => {
      expect(screen.getByText('This is a helpful AI response about functions')).toBeInTheDocument();
    });
  });

  it('handles API errors gracefully', async () => {
    mockApi.api.getAIChat.mockRejectedValueOnce(new Error('API Error'));

    render(<AIChat {...defaultProps} />);
    
    const textarea = screen.getByPlaceholderText('Ask me anything about your code...');
    
    fireEvent.change(textarea, { target: { value: 'Test message' } });
    fireEvent.keyPress(textarea, { key: 'Enter', code: 'Enter' });
    
    await waitFor(() => {
      expect(screen.getByText('Sorry, I encountered an error. Please try again.')).toBeInTheDocument();
    });
  });

  it('clears input after sending message', async () => {
    mockApi.api.getAIChat.mockResolvedValueOnce({
      content: 'Response'
    });

    render(<AIChat {...defaultProps} />);
    
    const textarea = screen.getByPlaceholderText('Ask me anything about your code...');
    
    fireEvent.change(textarea, { target: { value: 'Test message' } });
    fireEvent.keyPress(textarea, { key: 'Enter', code: 'Enter' });
    
    await waitFor(() => {
      expect(textarea).toHaveValue('');
    });
  });

  it('disables send button when input is empty', () => {
    render(<AIChat {...defaultProps} />);
    
    const sendButton = screen.getByRole('button', { name: /send/i });
    expect(sendButton).toBeDisabled();
  });

  it('enables send button when input has text', () => {
    render(<AIChat {...defaultProps} />);
    
    const textarea = screen.getByPlaceholderText('Ask me anything about your code...');
    const sendButton = screen.getByRole('button', { name: /send/i });
    
    fireEvent.change(textarea, { target: { value: 'Test message' } });
    
    expect(sendButton).not.toBeDisabled();
  });

  it('calls onClose when close button is clicked', () => {
    const onClose = vi.fn();
    render(<AIChat {...defaultProps} onClose={onClose} />);
    
    const closeButton = screen.getByRole('button', { name: /close/i });
    fireEvent.click(closeButton);
    
    expect(onClose).toHaveBeenCalled();
  });

  it('shows timestamps for messages', async () => {
    mockApi.api.getAIChat.mockResolvedValueOnce({
      content: 'Response'
    });

    render(<AIChat {...defaultProps} />);
    
    const textarea = screen.getByPlaceholderText('Ask me anything about your code...');
    
    fireEvent.change(textarea, { target: { value: 'Test message' } });
    fireEvent.keyPress(textarea, { key: 'Enter', code: 'Enter' });
    
    await waitFor(() => {
      // Should show timestamp in format like "12:34"
      expect(screen.getAllByText(/\d{1,2}:\d{2}/).length).toBeGreaterThan(0);
    });
  });

  it('renders markdown in AI responses', async () => {
    mockApi.api.getAIChat.mockResolvedValueOnce({
      content: 'Here is some code:\n\n```python\nprint("hello")\n```'
    });

    render(<AIChat {...defaultProps} />);
    
    const textarea = screen.getByPlaceholderText('Ask me anything about your code...');
    
    fireEvent.change(textarea, { target: { value: 'Show me code' } });
    fireEvent.keyPress(textarea, { key: 'Enter', code: 'Enter' });
    
    await waitFor(() => {
      expect(screen.getByText('Here is some code:')).toBeInTheDocument();
      // Code block should be rendered
      expect(screen.getByText('print("hello")')).toBeInTheDocument();
    });
  });
});