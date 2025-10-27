/**
 * API client for communicating with the FastAPI backend
 */

import { tauriApi } from './tauri-api';

// Types for API requests and responses
export interface SystemStatus {
  status: string;
  initialized: boolean;
  index_stats?: {
    status: string;
    document_count: number;
    source_file_count?: number;
    storage_path: string;
    collection_name: string;
  };
  target_directories?: string[];
  supported_formats?: string[];
}

export interface ChatMessage {
  message: string;
}

export interface ChatResponse {
  success: boolean;
  response?: string;
  error?: string;
}

export interface QueryRequest {
  query: string;
}

export interface QueryResponse {
  success: boolean;
  result?: {
    answer: string;
    sources: Array<{
      text: string;
      score?: number;
      metadata: Record<string, any>;
    }>;
    query: string;
    metadata: Record<string, any>;
  };
  error?: string;
}

export interface AddDocumentsRequest {
  file_paths: string[];
}

export interface DocumentOperationResponse {
  success: boolean;
  message?: string;
  stats?: {
    status: string;
    document_count: number;
    source_file_count?: number;
  };
  error?: string;
}

export interface SearchDocumentsRequest {
  query: string;
  top_k?: number;
}

export interface SearchDocumentsResponse {
  success: boolean;
  query: string;
  results: Array<{
    text: string;
    score?: number;
    metadata: Record<string, any>;
    node_id?: string;
  }>;
  count: number;
}

const API_BASE_URL = 'http://localhost:8000';

/**
 * Base API client class
 */
class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  // System endpoints
  async getSystemStatus(): Promise<SystemStatus> {
    return this.request<SystemStatus>('/api/system/status');
  }

  async getHealth(): Promise<{ status: string; service: string }> {
    return this.request<{ status: string; service: string }>('/api/system/health');
  }

  async getConfig(): Promise<{
    target_directories: string[];
    file_extensions: string[];
    max_results: number;
    chunk_size: number;
    chunk_overlap: number;
  }> {
    return this.request('/api/system/config');
  }

  // Document endpoints
  async refreshIndex(): Promise<DocumentOperationResponse> {
    return this.request<DocumentOperationResponse>('/api/documents/refresh', {
      method: 'POST',
    });
  }

  async addDocuments(filePaths: string[]): Promise<DocumentOperationResponse> {
    return this.request<DocumentOperationResponse>('/api/documents/add', {
      method: 'POST',
      body: JSON.stringify({ file_paths: filePaths }),
    });
  }

  async searchDocuments(query: string, topK: number = 10): Promise<SearchDocumentsResponse> {
    return this.request<SearchDocumentsResponse>('/api/documents/search', {
      method: 'POST',
      body: JSON.stringify({ query, top_k: topK }),
    });
  }

  async getDocumentStats(): Promise<{
    status: string;
    document_count: number;
    source_file_count?: number;
    storage_path?: string;
    collection_name?: string;
  }> {
    return this.request('/api/documents/stats');
  }

  // Chat endpoints
  async sendChatMessage(message: string): Promise<ChatResponse> {
    return this.request<ChatResponse>('/api/chat/message', {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
  }

  async queryDocuments(query: string): Promise<QueryResponse> {
    return this.request<QueryResponse>('/api/chat/query', {
      method: 'POST',
      body: JSON.stringify({ query }),
    });
  }
}

// Create and export a singleton instance
export const apiClient = new ApiClient();

// Enhanced API with backend management
class EnhancedApi {
  private client = apiClient;
  private backendStarted = false;

  async ensureBackendStarted(): Promise<void> {
    if (this.backendStarted) return;

    try {
      // Check if backend is already running
      const isHealthy = await tauriApi.checkBackendHealth();
      if (isHealthy) {
        this.backendStarted = true;
        return;
      }

      // Start the backend if not running
      console.log('Starting Python backend...');
      await tauriApi.startPythonBackend();

      // Wait a bit and check health
      await new Promise(resolve => setTimeout(resolve, 3000));
      const healthCheck = await tauriApi.checkBackendHealth();

      if (healthCheck) {
        this.backendStarted = true;
        console.log('✓ Backend started successfully');
      } else {
        throw new Error('Backend failed to start properly');
      }
    } catch (error) {
      console.error('Failed to ensure backend is started:', error);
      throw error;
    }
  }

  async safeRequest<T>(requestFn: () => Promise<T>): Promise<T> {
    try {
      await this.ensureBackendStarted();
      return await requestFn();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // System
  getSystemStatus = () => this.safeRequest(() => this.client.getSystemStatus());
  getHealth = () => this.safeRequest(() => this.client.getHealth());
  getConfig = () => this.safeRequest(() => this.client.getConfig());

  // Documents
  refreshIndex = () => this.safeRequest(() => this.client.refreshIndex());
  addDocuments = (filePaths: string[]) => this.safeRequest(() => this.client.addDocuments(filePaths));
  searchDocuments = (query: string, topK?: number) => this.safeRequest(() => this.client.searchDocuments(query, topK));
  getDocumentStats = () => this.safeRequest(() => this.client.getDocumentStats());

  // Chat
  sendChatMessage = (message: string) => this.safeRequest(() => this.client.sendChatMessage(message));
  queryDocuments = (query: string) => this.safeRequest(() => this.client.queryDocuments(query));

  // Backend management
  checkBackendHealth = () => tauriApi.checkBackendHealth();
  startBackend = () => tauriApi.startPythonBackend();
}

// Export enhanced API instance
export const api = new EnhancedApi();

export default api;