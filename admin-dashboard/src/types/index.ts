// Types based on the existing dashboard API structure

export interface AssistantConfig {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  plugins: PluginConfig[];
  status?: string;
}

export interface PluginConfig {
  name: string;
  enabled: boolean;
  tools: ToolConfig[];
  status?: string;
}

export interface ToolConfig {
  name: string;
  enabled: boolean;
}

export interface AvailablePlugin {
  name: string;
  description: string;
  tools: Array<{
    name: string;
    description: string;
  }>;
}

export interface AppSettings {
  [key: string]: any;
}

export interface LogEntry {
  level: string;
  timestamp: string;
  module: string;
  function: string;
  message: string;
  context?: Record<string, any>;
  correlation_id?: string;
}

export interface LogStatistics {
  total: number;
  by_level: Record<string, number>;
  by_module: Record<string, number>;
}

export interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  message?: string;
}

export type StatusLevel = 'ok' | 'warn' | 'error' | 'disabled' | 'unknown';