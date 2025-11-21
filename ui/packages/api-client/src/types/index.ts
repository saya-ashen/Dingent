

// -------------- app domain types --------------
export interface LoginRequest { email: string; password: string; }
export interface LoginResponse { access_token: string; token_type?: string; user?: any; }
export type AuthUser = {
  /** Id */
  id: string;
  /**
   * Email
   * Format: email
   */
  email: string;
  /** Full Name */
  full_name?: string | null;
  /** Role */
  role: string[];
};


export type LogItem = {
  timestamp: string;
  level: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL" | string;
  message: string;
  module?: string;
  function?: string;
  context?: Record<string, unknown>;
  correlation_id?: string;
};

export type LogStats = {
  total_logs: number;
  by_level: Record<string, number>;
  by_module: Record<string, number>;
  oldest_timestamp: string | null;
  newest_timestamp: string | null;
};

// export type PluginConfigItem = {
//   name: string;
//   type?: "string" | "integer";
//   required?: boolean;
//   secret?: boolean;
//   description?: string;
//   default?: unknown;
//   value?: unknown;
// };
type PluginConfigType = "string" | "float" | "integer" | "bool";
export interface PluginConfigItem {
  name: string;
  type: PluginConfigType;
  required: boolean;
  secret: boolean;
  description?: string | null;
  default?: string | number | boolean | null;
  value?: string | number | boolean | null;
}

export type PluginTool = { name: string; description?: string; enabled?: boolean; };

export type AssistantPlugin = {
  registry_id: string;
  display_name: string;
  status?: string;
  enabled?: boolean;
  config?: PluginConfigItem[];
  tools?: PluginTool[];
};

export type Assistant = {
  id: string;
  name: string;
  description?: string;
  enabled?: boolean;
  status?: string;
  plugins?: AssistantPlugin[];
  updatedAt?: string;
};

export type AppSettings = {
  llm?: { model?: string; base_url?: string; provider?: string; api_key?: string; };
  workflows?: { id: string; name: string; }[];
  current_workflow?: string;
};

export type PluginManifest = {
  registry_id: string;
  display_name: string;
  version?: string;
  description?: string;
  spec_version?: string;
  execution?: { mode?: string };
  dependencies?: string[];
};

import type { Edge, Node } from "@xyflow/react";
interface BaseWorkflowNode { id: string; position: { x: number; y: number }; }
export interface AssistantWorkflowNode extends BaseWorkflowNode {
  type: "assistant";
  data: { id: string; assistantId: string, isStart?: boolean; name: string; description?: string; };
}
export type WorkflowNode = Node<AssistantWorkflowNode["data"]>;
export type WorkflowEdge = Edge<{ mode?: "bidirectional" | "single" }>;
export type Workflow = {
  id: string;
  name: string;
  description?: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  created_at?: string;
  updated_at?: string;
};
export type WorkflowSummary = Pick<Workflow, "id" | "name" | "description">;
type ModelCost = { [modelName: string]: number; };
export type AnalyticsData = { total_budget: number; current_cost: number; model_cost: ModelCost; };

export interface OverviewAssistantItem { id: string; name: string; status: string; plugin_count: number; enabled_plugin_count: number; }
export interface OverviewPluginItem { id: string; name: string; version: string; tool_count: number; }
export interface OverviewWorkflowItem { id: string; name: string; }
export interface OverviewLogEntry { [k: string]: any; timestamp?: string; ts?: string; level?: string; module?: string; message?: string; context?: any; }
export interface OverviewData {
  assistants: { total: number; active: number; inactive: number; list: OverviewAssistantItem[]; };
  plugins: { installed_total: number; list: OverviewPluginItem[]; };
  workflows: { total: number; active_workflow_id: string | null; list: OverviewWorkflowItem[]; };
  logs: { recent: OverviewLogEntry[]; stats: Record<string, any>; };
  market: { metadata: any; plugin_updates: number; };
  llm: Record<string, any>;
}

export type MarketItem = {
  id: string; name: string; description?: string; version?: string; author?: string;
  category: "plugin" | "assistant" | "workflow";
  tags?: string[]; license?: string; readme?: string;
  downloads?: number; rating?: number; created_at?: string; updated_at?: string;
  is_installed?: boolean; installed_version?: string; update_available?: boolean;
};

export type MarketMetadata = {
  version: string;
  updated_at: string;
  categories: { plugins: number; assistants: number; workflows: number; };
};

export type MarketDownloadRequest = { item_id: string; category: "plugin" | "assistant" | "workflow"; isUpdate: boolean; };
export type MarketDownloadResponse = { success: boolean; message: string; installed_path?: string; };
export interface DisplayItem {
  type?: string;
  title?: string;
  columns?: string[];
  rows?: unknown[];
  content?: string;
  [k: string]: unknown;
}

export type Artifact = {
  version?: string;
  display: DisplayItem[];
  data?: unknown;
  metadata?: unknown;
  [k: string]: unknown;
}

