import axios from 'axios';
import type {
  Token,
  OfficerProfile,
  AnalyzeScanResponse,
  ScanRecord,
  DashboardStatistics,
  ChatRequest,
  ChatResponse
} from '../types/api';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  headers: {
    'Accept': 'application/json',
  },
});

// Interceptor to attach JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('legalmetrix_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const authApi = {
  login: async (username: string, password: string): Promise<Token> => {
    const response = await api.post<Token>('/api/auth/login', { username, password });
    return response.data;
  },
  register: async (payload: { username: string; password: string; email?: string; badge_number?: string; role?: string }): Promise<Token> => {
    await api.post('/api/auth/register', payload);
    return authApi.login(payload.username, payload.password);
  },
  getMe: async (): Promise<OfficerProfile> => {
    const response = await api.get<OfficerProfile>('/api/auth/me');
    return response.data;
  },
};

export const scanApi = {
  analyzeImage: async (
    file: File | Blob,
    options: {
      use_ensemble?: boolean;
      preprocessing_strategy?: string;
      brand_name?: string;
      persist?: boolean;
    } = {}
  ): Promise<AnalyzeScanResponse> => {
    const formData = new FormData();
    formData.append('file', file, 'package_scan.jpg');

    const params: Record<string, string | boolean> = {};
    if (options.use_ensemble !== undefined) params.use_ensemble = options.use_ensemble;
    if (options.preprocessing_strategy) params.preprocessing_strategy = options.preprocessing_strategy;
    if (options.brand_name) params.brand_name = options.brand_name;
    if (options.persist !== undefined) params.persist = options.persist;

    const response = await api.post<AnalyzeScanResponse>('/api/analyze', formData, {
      params,
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getScans: async (params: {
    limit?: number;
    offset?: number;
    status?: string;
    product_name?: string;
    officer_id?: number;
  } = {}): Promise<{ total: number; scans: ScanRecord[] }> => {
    const response = await api.get<{ total: number; scans: ScanRecord[] }>('/api/scans', { params });
    return response.data;
  },

  getScanById: async (id: number): Promise<ScanRecord> => {
    const response = await api.get<ScanRecord>(`/api/scans/${id}`);
    return response.data;
  },

  downloadPdfReportUrl: (id: number): string => {
    return `/api/scans/${id}/report.pdf`;
  },

  downloadPdfBlob: async (id: number): Promise<Blob> => {
    const response = await api.get(`/api/scans/${id}/report.pdf`, {
      responseType: 'blob',
    });
    return response.data;
  },
};

export const statsApi = {
  getDashboardStats: async (params: {
    start_date?: string;
    end_date?: string;
  } = {}): Promise<DashboardStatistics> => {
    const response = await api.get<DashboardStatistics>('/api/stats/dashboard', { params });
    return response.data;
  },
};

export const chatApi = {
  sendMessage: async (payload: ChatRequest): Promise<ChatResponse> => {
    const response = await api.post<ChatResponse>('/api/chat', payload);
    return response.data;
  },
};

export default api;
