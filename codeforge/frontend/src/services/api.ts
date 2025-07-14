/**
 * API Service
 */
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || `${window.location.protocol}//${window.location.hostname}:8000/api/v1`;

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

  explainCode: async (context: any) => {
    const response = await apiClient.post('/ai/explain', context);
    return response.data;
  },

  reviewCode: async (context: any) => {
    const response = await apiClient.post('/ai/review', context);
    return response.data;
  },

  fixBug: async (context: any) => {
    const response = await apiClient.post('/ai/fix', context);
    return response.data;
  },

  refactorCode: async (context: any) => {
    const response = await apiClient.post('/ai/refactor', context);
    return response.data;
  },

  generateTests: async (context: any) => {
    const response = await apiClient.post('/ai/generate-tests', context);
    return response.data;
  },

  generateDocs: async (context: any) => {
    const response = await apiClient.post('/ai/generate-docs', context);
    return response.data;
  },

  implementFeature: async (context: any) => {
    const response = await apiClient.post('/ai/implement-feature', context);
    return response.data;
  },

  getAIProviders: async () => {
    const response = await apiClient.get('/ai/providers');
    return response.data;
  },

  getAIChat: async (messages: any[]) => {
    const response = await apiClient.post('/ai/chat', { messages });
    return response.data;
  },

  // Clone
  cloneProject: async (options: any) => {
    const response = await apiClient.post('/clone/start', options);
    return response.data;
  },

  quickClone: async (projectId: string) => {
    const response = await apiClient.post(`/clone/quick/${projectId}`);
    return response.data;
  },

  getCloneStatus: async (cloneId: string) => {
    const response = await apiClient.get(`/clone/status/${cloneId}`);
    return response.data;
  },

  getCloneHistory: async () => {
    const response = await apiClient.get('/clone/history');
    return response.data;
  },

  getCloneTemplates: async () => {
    const response = await apiClient.get('/clone/templates');
    return response.data;
  },

  cloneTemplate: async (templateId: string, projectName?: string) => {
    const response = await apiClient.post(`/clone/template/${templateId}`, {
      project_name: projectName,
    });
    return response.data;
  },

  getCloneStats: async () => {
    const response = await apiClient.get('/clone/performance/stats');
    return response.data;
  },

  // Collaboration
  joinCollaborationSession: async (projectId: string) => {
    const response = await apiClient.post('/collaboration/sessions/join', {
      project_id: projectId,
    });
    return response.data;
  },

  leaveCollaborationSession: async (projectId: string) => {
    const response = await apiClient.post(`/collaboration/sessions/${projectId}/leave`);
    return response.data;
  },

  sendCollaborationOperation: async (projectId: string, operation: any) => {
    const response = await apiClient.post(`/collaboration/sessions/${projectId}/operations`, operation);
    return response.data;
  },

  updateCollaborationCursor: async (projectId: string, cursor: any) => {
    const response = await apiClient.post(`/collaboration/sessions/${projectId}/cursor`, cursor);
    return response.data;
  },

  getCollaborationState: async (projectId: string) => {
    const response = await apiClient.get(`/collaboration/sessions/${projectId}/state`);
    return response.data;
  },

  getCollaborationFileOperations: async (projectId: string, filePath: string, sinceVersion = 0) => {
    const response = await apiClient.get(`/collaboration/sessions/${projectId}/files/${filePath}/operations`, {
      params: { since_version: sinceVersion },
    });
    return response.data;
  },

  getActiveCollaborationSessions: async () => {
    const response = await apiClient.get('/collaboration/sessions/active');
    return response.data;
  },

  // Time-Travel Debugging
  startDebugSession: async (config: any) => {
    const response = await apiClient.post('/debug/sessions/start', config);
    return response.data;
  },

  endDebugSession: async (sessionId: string) => {
    const response = await apiClient.post(`/debug/sessions/${sessionId}/end`);
    return response.data;
  },

  captureDebugEvent: async (sessionId: string, event: any) => {
    const response = await apiClient.post(`/debug/sessions/${sessionId}/events`, event);
    return response.data;
  },

  travelToTime: async (request: any) => {
    const response = await apiClient.post('/debug/travel', request);
    return response.data;
  },

  stepBackInTime: async (request: any) => {
    const response = await apiClient.post('/debug/step-back', request);
    return response.data;
  },

  stepForwardInTime: async (request: any) => {
    const response = await apiClient.post('/debug/step-forward', request);
    return response.data;
  },

  getDebugTimeline: async (sessionId: string) => {
    const response = await apiClient.get(`/debug/sessions/${sessionId}/timeline`);
    return response.data;
  },

  searchDebugTimeline: async (sessionId: string, query: any, limit = 100) => {
    const response = await apiClient.post('/debug/search', {
      session_id: sessionId,
      query,
      limit,
    });
    return response.data;
  },

  getVariableChanges: async (sessionId: string, variableName: string, startEvent = 0, endEvent?: number) => {
    const response = await apiClient.get(`/debug/sessions/${sessionId}/variables/${variableName}/changes`, {
      params: { start_event: startEvent, end_event: endEvent },
    });
    return response.data;
  },

  getFunctionCalls: async (sessionId: string, functionName: string, startEvent = 0, endEvent?: number) => {
    const response = await apiClient.get(`/debug/sessions/${sessionId}/functions/${functionName}/calls`, {
      params: { start_event: startEvent, end_event: endEvent },
    });
    return response.data;
  },

  getActiveDebugSessions: async () => {
    const response = await apiClient.get('/debug/sessions/active');
    return response.data;
  },

  getDebugFeatures: async () => {
    const response = await apiClient.get('/debug/features');
    return response.data;
  },

  deleteDebugSession: async (sessionId: string) => {
    const response = await apiClient.delete(`/debug/sessions/${sessionId}`);
    return response.data;
  },

  // Deployment
  createDeployment: async (config: any) => {
    const response = await apiClient.post('/deploy/create', config);
    return response.data;
  },

  getDeployment: async (deploymentId: string) => {
    const response = await apiClient.get(`/deploy/deployments/${deploymentId}`);
    return response.data;
  },

  getDeploymentLogs: async (deploymentId: string) => {
    const response = await apiClient.get(`/deploy/deployments/${deploymentId}/logs`);
    return response.data;
  },

  cancelDeployment: async (deploymentId: string) => {
    const response = await apiClient.post(`/deploy/deployments/${deploymentId}/cancel`);
    return response.data;
  },

  redeployProject: async (deploymentId: string) => {
    const response = await apiClient.post(`/deploy/deployments/${deploymentId}/redeploy`);
    return response.data;
  },

  getProjectDeployments: async (projectId: string) => {
    const response = await apiClient.get(`/deploy/projects/${projectId}/deployments`);
    return response.data;
  },

  getUserDeployments: async () => {
    const response = await apiClient.get('/deploy/user/deployments');
    return response.data;
  },

  getDeploymentProviders: async (projectType?: string) => {
    const response = await apiClient.get('/deploy/providers', {
      params: projectType ? { project_type: projectType } : undefined,
    });
    return response.data;
  },

  quickDeploy: async (projectId: string, provider: string = 'vercel') => {
    const response = await apiClient.post(`/deploy/quick-deploy/${projectId}`, null, {
      params: { provider },
    });
    return response.data;
  },

  getDeploymentAnalytics: async (projectId: string) => {
    const response = await apiClient.get(`/deploy/analytics/${projectId}`);
    return response.data;
  },

  getDeploymentHealth: async () => {
    const response = await apiClient.get('/deploy/health');
    return response.data;
  },

  // Performance Monitoring
  getPerformanceDashboard: async () => {
    const response = await apiClient.get('/performance/dashboard');
    return response.data;
  },

  getPerformanceMetrics: async (params?: any) => {
    const response = await apiClient.get('/performance/metrics', { params });
    return response.data;
  },

  recordPerformanceMetric: async (metric: any) => {
    const response = await apiClient.post('/performance/metrics/record', metric);
    return response.data;
  },

  getSystemHealth: async () => {
    const response = await apiClient.get('/performance/health');
    return response.data;
  },

  getPerformanceInsights: async () => {
    const response = await apiClient.get('/performance/insights');
    return response.data;
  },

  getPerformanceAlerts: async (includeResolved = false) => {
    const response = await apiClient.get('/performance/alerts', {
      params: { include_resolved: includeResolved },
    });
    return response.data;
  },

  resolvePerformanceAlert: async (alertId: string) => {
    const response = await apiClient.post(`/performance/alerts/${alertId}/resolve`);
    return response.data;
  },

  getSystemStats: async () => {
    const response = await apiClient.get('/performance/system/stats');
    return response.data;
  },

  exportPerformanceMetrics: async (format = 'json', timeRange = 1440) => {
    const response = await apiClient.get('/performance/export', {
      params: { format, time_range: timeRange },
    });
    return response.data;
  },
};