import axios, { AxiosResponse } from 'axios';
import { 
  AssistantConfig, 
  PluginConfig, 
  AvailablePlugin, 
  AppSettings, 
  LogEntry, 
  LogStatistics,
  ApiResponse 
} from '@/types';

// Create axios instance with default config
const api = axios.create({
  baseURL: process.env.NODE_ENV === 'development' ? '/api' : 'http://127.0.0.1:2024',
  timeout: 120000, // 2 minutes, matching the Python HTTP_TIMEOUT
});

// Add request interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error);
    throw error;
  }
);

// App Settings API
export const appSettingsAPI = {
  async get(): Promise<AppSettings | null> {
    try {
      const response: AxiosResponse<AppSettings> = await api.get('/app_settings');
      return response.data;
    } catch (error) {
      console.error('Failed to fetch app settings:', error);
      return null;
    }
  },

  async save(settings: AppSettings): Promise<boolean> {
    try {
      await api.post('/app_settings', settings);
      return true;
    } catch (error) {
      console.error('Failed to save app settings:', error);
      return false;
    }
  }
};

// Assistants API
export const assistantsAPI = {
  async getAll(): Promise<AssistantConfig[] | null> {
    try {
      const response: AxiosResponse<AssistantConfig[]> = await api.get('/assistants');
      return response.data;
    } catch (error) {
      console.error('Failed to fetch assistants:', error);
      return null;
    }
  },

  async save(assistants: AssistantConfig[]): Promise<boolean> {
    try {
      await api.post('/assistants', assistants);
      return true;
    } catch (error) {
      console.error('Failed to save assistants:', error);
      return false;
    }
  },

  async addPlugin(assistantId: string, pluginName: string): Promise<boolean> {
    try {
      await api.post(`/assistants/${assistantId}/plugins/${pluginName}`);
      return true;
    } catch (error) {
      console.error('Failed to add plugin to assistant:', error);
      return false;
    }
  },

  async removePlugin(assistantId: string, pluginName: string): Promise<boolean> {
    try {
      await api.delete(`/assistants/${assistantId}/plugins/${pluginName}`);
      return true;
    } catch (error) {
      console.error('Failed to remove plugin from assistant:', error);
      return false;
    }
  }
};

// Plugins API
export const pluginsAPI = {
  async getAvailable(): Promise<AvailablePlugin[] | null> {
    try {
      const response: AxiosResponse<AvailablePlugin[]> = await api.get('/plugins');
      return response.data;
    } catch (error) {
      console.error('Failed to fetch available plugins:', error);
      return null;
    }
  },

  async remove(pluginName: string): Promise<boolean> {
    try {
      await api.delete(`/plugins/${pluginName}`);
      return true;
    } catch (error) {
      console.error('Failed to remove plugin:', error);
      return false;
    }
  }
};

// Logs API
export const logsAPI = {
  async get(params?: {
    level?: string;
    module?: string;
    limit?: number;
    search?: string;
  }): Promise<LogEntry[]> {
    try {
      const response: AxiosResponse<LogEntry[]> = await api.get('/logs', { params });
      return response.data;
    } catch (error) {
      console.error('Failed to fetch logs:', error);
      return [];
    }
  },

  async getStatistics(): Promise<LogStatistics | null> {
    try {
      const response: AxiosResponse<LogStatistics> = await api.get('/logs/statistics');
      return response.data;
    } catch (error) {
      console.error('Failed to fetch log statistics:', error);
      return null;
    }
  },

  async clearAll(): Promise<boolean> {
    try {
      await api.delete('/logs');
      return true;
    } catch (error) {
      console.error('Failed to clear logs:', error);
      return false;
    }
  }
};

export { api };