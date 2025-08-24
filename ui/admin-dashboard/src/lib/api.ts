import axios from "axios";
import type { AppSettings, Assistant, LogItem, LogStats, PluginManifest, Workflow } from "./types";

const BASE_URL = (import.meta.env.VITE_BACKEND_URL || "http://127.0.0.1:8000") + "/api/v1";
const HTTP_TIMEOUT = 120_000;

// 可选：从本地存储读取鉴权令牌
function getAuthToken(): string | null {
    return localStorage.getItem("DASHBOARD_TOKEN");
}

export const http = axios.create({
    baseURL: BASE_URL,
    timeout: HTTP_TIMEOUT
});

// 附加 Authorization（如果存在）
http.interceptors.request.use((config) => {
    const token = getAuthToken();
    if (token) {
        config.headers = config.headers || {};
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// 统一错误信息提取（与后端 detail 字段对齐）
function extractErrorMessage(err: unknown): string {
    if (axios.isAxiosError(err)) {
        const resp = err.response;
        if (resp?.data && typeof resp.data === "object" && "detail" in resp.data) {
            return String((resp.data as any).detail);
        }
        if (typeof resp?.data === "string") return resp.data;
        if (resp?.status) return `HTTP ${resp.status}`;
        return err.message || "Network error";
    }
    return String(err);
}

// --- Settings ---

export async function getAppSettings(): Promise<AppSettings | null> {
    try {
        const { data } = await http.get<AppSettings>("/settings");
        return data;
    } catch (err) {
        throw new Error(`Failed to fetch app settings: ${extractErrorMessage(err)}`);
    }
}

export async function saveAppSettings(payload: AppSettings): Promise<void> {
    try {
        // Use PATCH for partial updates
        await http.patch("/settings", payload);
    } catch (err) {
        throw new Error(`Failed to save app settings: ${extractErrorMessage(err)}`);
    }
}


// --- Assistants ---

export async function getAssistantsConfig(): Promise<Assistant[] | null> {
    try {
        const { data } = await http.get<Assistant[]>("/assistants");
        return data;
    } catch (err) {
        // Return mock data for development when backend is not available
        console.warn("Backend not available, returning mock assistants", err);
        return [
            {
                id: "support-bot",
                name: "Support Bot",
                description: "Handles customer support inquiries",
                enabled: true,
                status: "active",
                plugins: []
            },
            {
                id: "escalation-bot",
                name: "Escalation Bot",
                description: "Handles complex escalated issues",
                enabled: true,
                status: "active",
                plugins: []
            },
            {
                id: "data-analyst",
                name: "Data Analyst",
                description: "Analyzes customer data and generates reports",
                enabled: true,
                status: "active",
                plugins: []
            }
        ];
    }
}

export async function saveAssistantsConfig(payload: Assistant[]): Promise<void> {
    try {
        // Use PUT to replace the entire collection
        await http.put("/assistants", payload);
    } catch (err) {
        throw new Error(`Failed to save assistants configuration: ${extractErrorMessage(err)}`);
    }
}

export async function addAssistant(name: string, description: string): Promise<Assistant> {
    try {
        // POST to the collection endpoint
        const { data } = await http.post<Assistant>("/assistants", { name, description });
        return data;
    } catch (err) {
        throw new Error(`Failed to add assistant '${name}': ${extractErrorMessage(err)}`);
    }
}

export async function deleteAssistant(assistantId: string): Promise<void> {
    try {
        // Use DELETE on the specific resource URL
        await http.delete(`/assistants/${assistantId}`);
    } catch (err) {
        throw new Error(`Failed to delete assistant '${assistantId}': ${extractErrorMessage(err)}`);
    }
}

export async function addPluginToAssistant(assistantId: string, pluginName: string): Promise<void> {
    try {
        // POST to the plugins sub-collection with the name in the body
        await http.post(`/assistants/${assistantId}/plugins`, { plugin_name: pluginName });
    } catch (err) {
        throw new Error(`Failed to add plugin '${pluginName}': ${extractErrorMessage(err)}`);
    }
}

export async function removePluginFromAssistant(assistantId: string, pluginName: string): Promise<void> {
    try {
        // Use DELETE on the specific plugin sub-resource URL
        await http.delete(`/assistants/${assistantId}/plugins/${pluginName}`);
    } catch (err) {
        throw new Error(`Failed to remove plugin '${pluginName}': ${extractErrorMessage(err)}`);
    }
}


// --- Plugins ---

export async function getAvailablePlugins(): Promise<PluginManifest[] | null> {
    try {
        // Corrected collection URL
        const { data } = await http.get<PluginManifest[]>("/plugins");
        return data;
    } catch (err) {
        throw new Error(`Failed to fetch available plugins: ${extractErrorMessage(err)}`);
    }
}

export async function deletePlugin(pluginName: string): Promise<void> {
    try {
        // Use DELETE on the specific plugin resource URL
        await http.delete(`/plugins/${pluginName}`);
    } catch (err) {
        throw new Error(`Failed to delete plugin '${pluginName}': ${extractErrorMessage(err)}`);
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
        return { total_logs: 0, by_level: {}, by_module: {}, oldest_timestamp: null, newest_timestamp: null };
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
        return [
            {
                id: "mock-workflow-1",
                name: "Customer Support Flow",
                description: "Handles customer inquiries and escalations",
                nodes: [
                    {
                        id: "node-1",
                        type: "assistant",
                        position: { x: 100, y: 100 },
                        data: {
                            assistantId: "support-bot",
                            assistantName: "Support Bot",
                            description: "Initial customer support assistant"
                        }
                    },
                    {
                        id: "node-2",
                        type: "assistant",
                        position: { x: 300, y: 100 },
                        data: {
                            assistantId: "escalation-bot",
                            assistantName: "Escalation Bot",
                            description: "Handles complex issues"
                        }
                    }
                ],
                edges: [
                    {
                        id: "edge-1",
                        source: "node-1",
                        target: "node-2",
                        type: "default",
                        data: { label: "Escalate complex issues" }
                    }
                ],
                created_at: "2024-01-01T10:00:00Z",
                updated_at: "2024-01-01T10:00:00Z"
            }
        ];
    }
}

export async function getWorkflow(workflowId: string): Promise<Workflow | null> {
    try {
        const { data } = await http.get<Workflow>(`/workflows/${workflowId}`);
        return data;
    } catch (err) {
        throw new Error(`Failed to fetch workflow '${workflowId}': ${extractErrorMessage(err)}`);
    }
}

export async function saveWorkflow(workflow: Workflow): Promise<Workflow> {
    try {
        console.log("Saving workflow", workflow);
        const { data } = await http.put<Workflow>(`/workflows/${workflow.id}`, workflow);
        return data;
    } catch (err) {
        // Mock save for development
        console.warn("Backend not available, mocking workflow save");
        return { ...workflow, updated_at: new Date().toISOString() };
    }
}

export async function createWorkflow(name: string, description?: string): Promise<Workflow> {
    try {
        const { data } = await http.post<Workflow>("/workflows", { name, description });
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
            updated_at: new Date().toISOString()
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
