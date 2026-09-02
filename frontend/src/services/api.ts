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
    files: (File | Blob)[] | File | Blob,
    options: {
      use_ensemble?: boolean;
      preprocessing_strategy?: string;
      brand_name?: string;
      persist?: boolean;
      input_type?: 'physical_package' | 'ecommerce_listing';
      merge_strategy?: string;
    } = {}
  ): Promise<AnalyzeScanResponse> => {
    const formData = new FormData();

    if (Array.isArray(files)) {
      files.forEach((f, idx) => {
        const filename = f instanceof File ? f.name : `package_panel_${idx + 1}.jpg`;
        formData.append('files', f, filename);
      });
      if (files.length > 0) {
        // Legacy single file fallback
        const singleFile = files[0];
        const fname = singleFile instanceof File ? singleFile.name : 'package_scan.jpg';
        formData.append('file', singleFile, fname);
      }
    } else {
      const filename = files instanceof File ? files.name : 'package_scan.jpg';
      formData.append('file', files, filename);
      formData.append('files', files, filename);
    }

    const params: Record<string, string | boolean> = {};
    if (options.use_ensemble !== undefined) params.use_ensemble = options.use_ensemble;
    if (options.preprocessing_strategy) params.preprocessing_strategy = options.preprocessing_strategy;
    if (options.brand_name) params.brand_name = options.brand_name;
    if (options.persist !== undefined) params.persist = options.persist;
    if (options.input_type) params.input_type = options.input_type;
    if (options.merge_strategy) params.merge_strategy = options.merge_strategy;

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

  downloadCsvBlob: async (id: number): Promise<Blob> => {
    const response = await api.get(`/api/scans/${id}/export/csv`, {
      responseType: 'blob',
    });
    return response.data;
  },

  downloadXlsxBlob: async (id: number): Promise<Blob> => {
    const response = await api.get(`/api/scans/${id}/export/xlsx`, {
      responseType: 'blob',
    });
    return response.data;
  },

  downloadDocxBlob: async (id: number): Promise<Blob> => {
    const response = await api.get(`/api/scans/${id}/export/docx`, {
      responseType: 'blob',
    });
    return response.data;
  },

  downloadBulkXlsxBlob: async (params?: {
    status?: string;
    officer_id?: number;
    product_name?: string;
    limit?: number;
    offset?: number;
  }): Promise<Blob> => {
    const response = await api.get('/api/scans/export/xlsx', {
      params,
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
