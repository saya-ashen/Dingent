"use client";
import type {
  AppSettings,
  Assistant,
  LogItem,
  LogStats,
  PluginManifest,
  Workflow,
  MarketItem,
  MarketMetadata,
  MarketDownloadRequest,
  MarketDownloadResponse,
  OverviewData,
  AnalyticsData,
  LoginRequest,
  LoginResponse,
} from "./types/index.ts";
import { createHttpInstance, extractErrorMessage } from "./http";
import { createDashboardApi } from "./dashboard";
import { createAuthApi } from "./auth";

const BASE_URL = (process.env.NEXT_PUBLIC_BACKEND_URL || "") + "/api/v1/dashboard";

export async function addAssistant(
  name: string,
  description: string,
): Promise<Assistant> {
  try {
    // POST to the collection endpoint
    const { data } = await http.post<Assistant>("/assistants", {
      name,
      description,
    });
    return data;
  } catch (err) {
    throw new Error(
      `Failed to add assistant '${name}': ${extractErrorMessage(err)}`,
    );
  }
}

export async function deleteAssistant(assistantId: string): Promise<void> {
  try {
    // Use DELETE on the specific resource URL
    await http.delete(`/assistants/${assistantId}`);
  } catch (err) {
    throw new Error(
      `Failed to delete assistant '${assistantId}': ${extractErrorMessage(err)}`,
    );
  }
}

export async function addPluginToAssistant(
  assistantId: string,
  pluginId: string,
): Promise<void> {
  try {
    // POST to the plugins sub-collection with the name in the body
    await http.post(`/assistants/${assistantId}/plugins`, {
      plugin_id: pluginId,
    });
  } catch (err) {
    throw new Error(
      `Failed to add plugin '${pluginId}': ${extractErrorMessage(err)}`,
    );
  }
}

export async function removePluginFromAssistant(
  assistantId: string,
  pluginId: string,
): Promise<void> {
  try {
    // Use DELETE on the specific plugin sub-resource URL
    await http.delete(`/assistants/${assistantId}/plugins/${pluginId}`);
  } catch (err) {
    throw new Error(
      `Failed to remove plugin '${pluginId}': ${extractErrorMessage(err)}`,
    );
  }
}

export async function updateAssistant(
  assistantId: string,
  payload: Partial<Assistant>,
): Promise<Assistant> {
  try {
    const transformedPayload = structuredClone(payload);

    if (transformedPayload.plugins) {
      transformedPayload.plugins.forEach((plugin) => {
        if (plugin.config && Array.isArray(plugin.config)) {
          const newConfigObject = plugin.config.reduce(
            (acc, item) => {
              if (item.value !== undefined && item.value !== null) {
                acc[item.name] = item.value;
              }
              return acc;
            },
            {} as Record<string, unknown>,
          );
          (plugin as any).config = newConfigObject;
        }
      });
    }

    const { data } = await http.patch(
      `/assistants/${assistantId}`,
      transformedPayload,
    );

    return data;
  } catch (err) {
    throw new Error(`Failed to update assistant: ${extractErrorMessage(err)}`);
  }
}

// --- Plugins ---

export async function getAvailablePlugins(): Promise<PluginManifest[] | null> {
  try {
    // Corrected collection URL
    const { data } = await http.get<PluginManifest[]>("/plugins");
    return data;
  } catch (err) {
    throw new Error(
      `Failed to fetch available plugins: ${extractErrorMessage(err)}`,
    );
  }
}

export async function deletePlugin(pluginId: string): Promise<void> {
  try {
    // Use DELETE on the specific plugin resource URL
    await http.delete(`/plugins/${pluginId}`);
  } catch (err) {
    throw new Error(
      `Failed to delete plugin '${pluginId}': ${extractErrorMessage(err)}`,
    );
  }
}

// --- Logs ---

export async function getLogs(params: {
  level?: string | null;
  module?: string | null;
  limit?: number | null;
  search?: string | null;
}): Promise<LogItem[]> {
  try {
    // Use GET and pass filters as query parameters
    const { data } = await http.get<LogItem[]>("/logs", { params });
    return data;
  } catch (err) {
    throw new Error(`Failed to fetch logs: ${extractErrorMessage(err)}`);
  }
}

export async function getLogStatistics(): Promise<LogStats> {
  try {
    // Corrected nested URL
    const { data } = await http.get<LogStats>("/logs/stats");
    return data;
  } catch {
    // Default value on failure
    return {
      total_logs: 0,
      by_level: {},
      by_module: {},
      oldest_timestamp: null,
      newest_timestamp: null,
    };
  }
}

// Assuming the backend provides a DELETE /logs endpoint to clear all logs
export async function clearAllLogs(): Promise<boolean> {
  try {
    await http.delete("/logs/clear"); // Using a more specific clear endpoint
    return true;
  } catch {
    return false;
  }
}

// --- Workflows ---

export async function getWorkflows(): Promise<Workflow[] | null> {
  try {
    const { data } = await http.get<Workflow[]>("/workflows");
    return data;
  } catch (err) {
    // Return mock data for development when backend is not available
    console.warn("Backend not available, returning mock workflows", err);
    return [];
  }
}

export async function getWorkflow(
  workflowId: string,
): Promise<Workflow | null> {
  try {
    const { data } = await http.get<Workflow>(`/workflows/${workflowId}`);
    return data;
  } catch (err) {
    throw new Error(
      `Failed to fetch workflow '${workflowId}': ${extractErrorMessage(err)}`,
    );
  }
}

export async function saveWorkflow(workflow: Workflow): Promise<Workflow> {
  try {
    console.log("Saving workflow", workflow);
    const { data } = await http.put<Workflow>(
      `/workflows/${workflow.id}`,
      workflow,
    );
    return data;
  } catch (err) {
    // Mock save for development
    console.warn("Backend not available, mocking workflow save");
    return { ...workflow, updated_at: new Date().toISOString() };
  }
}

export async function createWorkflow(
  name: string,
  description?: string,
): Promise<Workflow> {
  try {
    const { data } = await http.post<Workflow>("/workflows", {
      name,
      description,
    });
    return data;
  } catch (err) {
    // Mock create for development
    console.warn("Backend not available, mocking workflow creation");
    return {
      id: `mock-${Date.now()}`,
      name,
      description,
      nodes: [],
      edges: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
  }
}

export async function deleteWorkflow(workflowId: string): Promise<void> {
  try {
    await http.delete(`/workflows/${workflowId}`);
  } catch (err) {
    // Mock delete for development
    console.warn("Backend not available, mocking workflow deletion");
    return;
  }
}

// --- Market ---

export async function getMarketMetadata(): Promise<MarketMetadata | null> {
  try {
    const { data } = await http.get<MarketMetadata>("/market/metadata");
    return data;
  } catch (err) {
    console.warn("Backend not available, returning mock market metadata", err);
    // Mock data for development
    return {
      version: "1.0.0",
      updated_at: new Date().toISOString(),
      categories: {
        plugins: 15,
        assistants: 8,
        workflows: 5,
      },
    };
  }
}

export async function getMarketItems(
  category: "all" | "plugin" | "assistant" | "workflow",
): Promise<MarketItem[] | null> {
  try {
    const url = category
      ? `/market/items?category=${category}`
      : "/market/items";
    const { data } = await http.get<MarketItem[]>(url);
    return data;
  } catch (err) {
    console.warn("Backend not available, returning mock market items", err);
    // Mock data for development
    return [];
  }
}

export async function downloadMarketItem(
  request: MarketDownloadRequest,
): Promise<MarketDownloadResponse> {
  try {
    const { data } = await http.post<MarketDownloadResponse>(
      "/market/download",
      request,
    );
    return data;
  } catch (err) {
    throw new Error(
      `Failed to download ${request.category} '${request.item_id}': ${extractErrorMessage(err)}`,
    );
  }
}

export async function getMarketItemReadme(
  itemId: string,
): Promise<string | null> {
  try {
    const { data } = await http.get<{ readme: string }>(
      `/market/items/${itemId}/readme`,
    );
    return data.readme;
  } catch (err) {
    console.warn("Failed to fetch readme for", itemId, err);
    return null;
  }
}

const AUTH_TOKEN_KEY = "APP_AUTH_TOKEN";

// Base URL for general API calls (like auth)
const API_BASE_URL = (process.env.NEXT_PUBLIC_BACKEND_URL || "") + "/api/v1";

// Base URL for dashboard-specific calls
const DASHBOARD_API_BASE_URL = API_BASE_URL + "/dashboard";

// --- Client Instances ---

// A general HTTP client for shared endpoints
const http = createHttpInstance(API_BASE_URL, AUTH_TOKEN_KEY);
const dashboardHttp = createHttpInstance(DASHBOARD_API_BASE_URL, AUTH_TOKEN_KEY);

export const dashboardApi = {
  ...createDashboardApi(dashboardHttp),
};
export const api = {
  ...createAuthApi(http),
};
export type * from "./types/index.js";
