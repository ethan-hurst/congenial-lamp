/**
 * API Service
 */
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// Create axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle auth errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear auth and redirect to login
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const api = {
  // Auth
  login: async (email: string, password: string) => {
    const response = await apiClient.post('/auth/login', { email, password });
    return response.data;
  },

  signup: async (data: { email: string; username: string; password: string }) => {
    const response = await apiClient.post('/auth/signup', data);
    return response.data;
  },

  // Projects
  getProjects: async () => {
    const response = await apiClient.get('/projects');
    return response.data;
  },

  getProject: async (projectId: string) => {
    const response = await apiClient.get(`/projects/${projectId}`);
    return response.data;
  },

  createProject: async (data: any) => {
    const response = await apiClient.post('/projects', data);
    return response.data;
  },

  updateProject: async (projectId: string, data: any) => {
    const response = await apiClient.put(`/projects/${projectId}`, data);
    return response.data;
  },

  deleteProject: async (projectId: string) => {
    const response = await apiClient.delete(`/projects/${projectId}`);
    return response.data;
  },

  // Files
  getFiles: async (projectId: string, path: string = '/') => {
    const response = await apiClient.get(`/projects/${projectId}/files`, {
      params: { path },
    });
    return response.data;
  },

  getFile: async (projectId: string, filePath: string) => {
    const response = await apiClient.get(`/projects/${projectId}/files${filePath}`);
    return response.data;
  },

  createFile: async (projectId: string, filePath: string, content: string) => {
    const response = await apiClient.post(`/projects/${projectId}/files${filePath}`, {
      content,
    });
    return response.data;
  },

  updateFile: async (projectId: string, filePath: string, content: string) => {
    const response = await apiClient.put(`/projects/${projectId}/files${filePath}`, {
      content,
    });
    return response.data;
  },

  deleteFile: async (projectId: string, filePath: string) => {
    const response = await apiClient.delete(`/projects/${projectId}/files${filePath}`);
    return response.data;
  },

  // Containers
  createContainer: async (projectId: string, config: any) => {
    const response = await apiClient.post('/containers/create', {
      project_id: projectId,
      ...config,
    });
    return response.data;
  },

  getContainerStats: async (containerId: string) => {
    const response = await apiClient.get(`/containers/${containerId}/stats`);
    return response.data;
  },

  stopContainer: async (containerId: string) => {
    const response = await apiClient.delete(`/containers/${containerId}`);
    return response.data;
  },

  // Credits
  getUserCredits: async () => {
    const response = await apiClient.get('/credits/balance');
    return response.data;
  },

  getCreditHistory: async () => {
    const response = await apiClient.get('/credits/history');
    return response.data;
  },

  purchaseCredits: async (amount: number) => {
    const response = await apiClient.post('/credits/purchase', { amount });
    return response.data;
  },

  // AI
  getAICompletion: async (context: any) => {
    const response = await apiClient.post('/ai/complete', context);
    return response.data;
  },

  getAIChat: async (messages: any[]) => {
    const response = await apiClient.post('/ai/chat', { messages });
    return response.data;
  },
};