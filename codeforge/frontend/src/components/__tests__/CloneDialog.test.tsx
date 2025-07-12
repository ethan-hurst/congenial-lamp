/**
 * Tests for Clone Dialog Component
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { CloneDialog } from '../Clone/CloneDialog';
import * as api from '../../services/api';

// Mock the API
vi.mock('../../services/api');
const mockApi = vi.mocked(api);

// Mock the project store
const mockAddProject = vi.fn();
const mockSetCurrentProject = vi.fn();

vi.mock('../../stores/projectStore', () => ({
  useProjectStore: () => ({
    addProject: mockAddProject,
    setCurrentProject: mockSetCurrentProject
  })
}));

describe('CloneDialog', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    projectId: 'source-project-123',
    projectName: 'Source Project',
    onCloneComplete: vi.fn()
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders when open', () => {
    render(<CloneDialog {...defaultProps} />);
    
    expect(screen.getByText('Clone Project')).toBeInTheDocument();
    expect(screen.getByText('Source Project')).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    render(<CloneDialog {...defaultProps} isOpen={false} />);
    
    expect(screen.queryByText('Clone Project')).not.toBeInTheDocument();
  });

  it('shows quick clone option', () => {
    render(<CloneDialog {...defaultProps} />);
    
    expect(screen.getByText('Quick Clone')).toBeInTheDocument();
    expect(screen.getByText(/Ultra-fast clone/)).toBeInTheDocument();
    expect(screen.getByText('< 0.5s')).toBeInTheDocument();
  });

  it('shows custom clone options', () => {
    render(<CloneDialog {...defaultProps} />);
    
    expect(screen.getByText('Custom Clone')).toBeInTheDocument();
    expect(screen.getByLabelText('Project Name')).toBeInTheDocument();
    expect(screen.getByText('Include Dependencies')).toBeInTheDocument();
    expect(screen.getByText('Include Containers')).toBeInTheDocument();
    expect(screen.getByText('Include Secrets')).toBeInTheDocument();
    expect(screen.getByText('Preserve State')).toBeInTheDocument();
  });

  it('updates clone name input', () => {
    render(<CloneDialog {...defaultProps} />);
    
    const nameInput = screen.getByLabelText('Project Name');
    fireEvent.change(nameInput, { target: { value: 'My Custom Clone' } });
    
    expect(nameInput).toHaveValue('My Custom Clone');
  });

  it('toggles clone options', () => {
    render(<CloneDialog {...defaultProps} />);
    
    const dependenciesToggle = screen.getByRole('checkbox', { name: /dependencies/i });
    expect(dependenciesToggle).toBeChecked();
    
    fireEvent.click(dependenciesToggle);
    expect(dependenciesToggle).not.toBeChecked();
  });

  it('updates estimated time based on options', () => {
    render(<CloneDialog {...defaultProps} />);
    
    // Should show initial estimate
    expect(screen.getByText(/< 1 second/)).toBeInTheDocument();
    
    // Toggle all options off to reduce time
    const toggles = screen.getAllByRole('checkbox');
    toggles.forEach(toggle => {
      if (toggle.checked) {
        fireEvent.click(toggle);
      }
    });
    
    // Should still show estimated time
    expect(screen.getByText(/Estimated time:/)).toBeInTheDocument();
  });

  it('performs quick clone', async () => {
    mockApi.api.quickClone.mockResolvedValueOnce({
      success: true,
      message: 'Ultra-fast clone completed in 0.4 seconds',
      new_project_id: 'cloned-project-456',
      performance: {
        time_seconds: 0.4,
        files_cloned: 15
      }
    });

    render(<CloneDialog {...defaultProps} />);
    
    const quickCloneButton = screen.getByRole('button', { name: /quick clone/i });
    fireEvent.click(quickCloneButton);
    
    await waitFor(() => {
      expect(mockApi.api.quickClone).toHaveBeenCalledWith('source-project-123');
    });
  });

  it('performs custom clone', async () => {
    mockApi.api.cloneProject.mockResolvedValueOnce({
      success: true,
      clone_id: 'clone-123',
      new_project_id: 'cloned-project-456',
      message: 'Project cloned successfully in 0.8 seconds',
      cloned_files: 25,
      total_time_seconds: 0.8,
      performance_metrics: {}
    });

    render(<CloneDialog {...defaultProps} />);
    
    const nameInput = screen.getByLabelText('Project Name');
    fireEvent.change(nameInput, { target: { value: 'My Clone' } });
    
    const cloneButton = screen.getByRole('button', { name: /clone project/i });
    fireEvent.click(cloneButton);
    
    await waitFor(() => {
      expect(mockApi.api.cloneProject).toHaveBeenCalledWith({
        project_id: 'source-project-123',
        clone_name: 'My Clone',
        include_dependencies: true,
        include_containers: true,
        include_secrets: false,
        preserve_state: true
      });
    });
  });

  it('shows success result after clone', async () => {
    mockApi.api.cloneProject.mockResolvedValueOnce({
      success: true,
      clone_id: 'clone-123',
      new_project_id: 'cloned-project-456',
      message: 'Project cloned successfully in 0.8 seconds',
      cloned_files: 25,
      total_time_seconds: 0.8,
      performance_metrics: {}
    });

    render(<CloneDialog {...defaultProps} />);
    
    const cloneButton = screen.getByRole('button', { name: /clone project/i });
    fireEvent.click(cloneButton);
    
    await waitFor(() => {
      expect(screen.getByText('Clone Successful!')).toBeInTheDocument();
      expect(screen.getByText(/successfully in 0.8 seconds/)).toBeInTheDocument();
      expect(screen.getByText('25')).toBeInTheDocument(); // cloned files
    });
  });

  it('adds cloned project to store', async () => {
    const onCloneComplete = vi.fn();
    
    mockApi.api.cloneProject.mockResolvedValueOnce({
      success: true,
      clone_id: 'clone-123',
      new_project_id: 'cloned-project-456',
      message: 'Success',
      cloned_files: 25,
      total_time_seconds: 0.8,
      performance_metrics: {}
    });

    render(<CloneDialog {...defaultProps} onCloneComplete={onCloneComplete} />);
    
    const nameInput = screen.getByLabelText('Project Name');
    fireEvent.change(nameInput, { target: { value: 'My Clone' } });
    
    const cloneButton = screen.getByRole('button', { name: /clone project/i });
    fireEvent.click(cloneButton);
    
    await waitFor(() => {
      expect(mockAddProject).toHaveBeenCalledWith({
        id: 'cloned-project-456',
        name: 'My Clone',
        description: 'Cloned from Source Project',
        language: 'multi',
        template: 'clone',
        created_at: expect.any(String),
        updated_at: expect.any(String)
      });
      
      expect(onCloneComplete).toHaveBeenCalledWith('cloned-project-456');
    });
  });

  it('handles clone errors', async () => {
    mockApi.api.cloneProject.mockRejectedValueOnce({
      response: {
        data: {
          detail: 'Clone failed: Source project not found'
        }
      }
    });

    render(<CloneDialog {...defaultProps} />);
    
    const cloneButton = screen.getByRole('button', { name: /clone project/i });
    fireEvent.click(cloneButton);
    
    await waitFor(() => {
      expect(screen.getByText('Clone failed: Source project not found')).toBeInTheDocument();
    });
  });

  it('disables clone button when name is empty', () => {
    render(<CloneDialog {...defaultProps} />);
    
    const nameInput = screen.getByLabelText('Project Name');
    fireEvent.change(nameInput, { target: { value: '' } });
    
    const cloneButton = screen.getByRole('button', { name: /clone project/i });
    expect(cloneButton).toBeDisabled();
  });

  it('shows loading state during clone', async () => {
    mockApi.api.cloneProject.mockImplementation(() => 
      new Promise(resolve => setTimeout(() => resolve({
        success: true,
        clone_id: 'clone-123',
        new_project_id: 'cloned-project-456',
        message: 'Success',
        cloned_files: 25,
        total_time_seconds: 0.8,
        performance_metrics: {}
      }), 100))
    );

    render(<CloneDialog {...defaultProps} />);
    
    const cloneButton = screen.getByRole('button', { name: /clone project/i });
    fireEvent.click(cloneButton);
    
    // Should show loading spinner
    await waitFor(() => {
      expect(cloneButton).toBeDisabled();
    });
  });

  it('calls onClose when cancel is clicked', () => {
    const onClose = vi.fn();
    render(<CloneDialog {...defaultProps} onClose={onClose} />);
    
    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    fireEvent.click(cancelButton);
    
    expect(onClose).toHaveBeenCalled();
  });

  it('calls onClose when X button is clicked', () => {
    const onClose = vi.fn();
    render(<CloneDialog {...defaultProps} onClose={onClose} />);
    
    const closeButton = screen.getByRole('button', { name: /close/i });
    fireEvent.click(closeButton);
    
    expect(onClose).toHaveBeenCalled();
  });

  it('opens project after successful clone', async () => {
    mockApi.api.cloneProject.mockResolvedValueOnce({
      success: true,
      clone_id: 'clone-123',
      new_project_id: 'cloned-project-456',
      message: 'Success',
      cloned_files: 25,
      total_time_seconds: 0.8,
      performance_metrics: {}
    });

    const onClose = vi.fn();
    render(<CloneDialog {...defaultProps} onClose={onClose} />);
    
    const cloneButton = screen.getByRole('button', { name: /clone project/i });
    fireEvent.click(cloneButton);
    
    await waitFor(() => {
      expect(screen.getByText('Open Project')).toBeInTheDocument();
    });
    
    const openButton = screen.getByRole('button', { name: /open project/i });
    fireEvent.click(openButton);
    
    expect(mockSetCurrentProject).toHaveBeenCalledWith('cloned-project-456');
    expect(onClose).toHaveBeenCalled();
  });

  it('shows performance metrics in success state', async () => {
    mockApi.api.quickClone.mockResolvedValueOnce({
      success: true,
      message: 'Success',
      new_project_id: 'cloned-project-456',
      performance: {
        time_seconds: 0.4,
        files_cloned: 15,
        speed_rating: '⚡ Ultra Fast'
      }
    });

    render(<CloneDialog {...defaultProps} />);
    
    const quickCloneButton = screen.getByRole('button', { name: /quick clone/i });
    fireEvent.click(quickCloneButton);
    
    await waitFor(() => {
      expect(screen.getByText('15')).toBeInTheDocument(); // files
      expect(screen.getByText('0.400s')).toBeInTheDocument(); // time
    });
  });
});