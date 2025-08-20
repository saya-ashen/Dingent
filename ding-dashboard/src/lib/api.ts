import axios from "axios";
import type { AppSettings, Assistant, LogItem, LogStats, PluginManifest } from "./types";

const BASE_URL = import.meta.env.VITE_BACKEND_URL || "/api/";
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
        const { data } = await http.get<AppSettings>("/config/settings");
        return data;
    } catch (err) {
        throw new Error(`Failed to fetch app settings: ${extractErrorMessage(err)}`);
    }
}

export async function saveAppSettings(payload: AppSettings): Promise<void> {
    try {
        await http.post("/config/settings", payload);
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
        throw new Error(`Failed to fetch assistants configuration: ${extractErrorMessage(err)}`);
    }
}

export async function saveAssistantsConfig(payload: Assistant[]): Promise<void> {
    try {
        await http.post("/assistants", payload);
    } catch (err) {
        throw new Error(`Failed to save assistants configuration: ${extractErrorMessage(err)}`);
    }
}

export async function addPluginToAssistant(assistantId: string, pluginName: string): Promise<void> {
    try {
        await http.post(`/assistants/${assistantId}/add_plugin`, null, { params: { plugin_name: pluginName } });
    } catch (err) {
        throw new Error(`Failed to add plugin '${pluginName}': ${extractErrorMessage(err)}`);
    }
}

export async function removePluginFromAssistant(assistantId: string, pluginName: string): Promise<void> {
    try {
        await http.post(`/assistants/${assistantId}/remove_plugin`, null, { params: { plugin_name: pluginName } });
    } catch (err) {
        throw new Error(`Failed to remove plugin '${pluginName}': ${extractErrorMessage(err)}`);
    }
}

// --- Plugins ---
export async function getAvailablePlugins(): Promise<PluginManifest[] | null> {
    try {
        const { data } = await http.get<PluginManifest[]>("/plugins/list");
        return data;
    } catch (err) {
        throw new Error(`Failed to fetch available plugins: ${extractErrorMessage(err)}`);
    }
}

export async function deletePlugin(pluginName: string): Promise<void> {
    try {
        await http.post("/plugins/remove", { plugin_name: pluginName });
    } catch (err) {
        throw new Error(`Failed to delete plugin '${pluginName}': ${extractErrorMessage(err)}`);
    }
}

// --- Logs ---
export async function getLogs(params: { level?: string | null; module?: string | null; limit?: number | null; search?: string | null; }): Promise<LogItem[]> {
    try {
        const body = {
            level: params.level ?? null,
            module: params.module ?? null,
            limit: params.limit ?? null,
            search: params.search ?? null
        };
        const { data } = await http.post<LogItem[]>("/app/logs", body);
        return data;
    } catch (err) {
        throw new Error(`Failed to fetch logs: ${extractErrorMessage(err)}`);
    }
}

export async function getLogStatistics(): Promise<LogStats> {
    try {
        const { data } = await http.get<LogStats>("/app/log_statistics");
        return data;
    } catch {
        return { total_logs: 0, by_level: {}, by_module: {}, oldest_timestamp: null, newest_timestamp: null };
    }
}

// 可选：如果后端提供 /app/logs/clear 端点，则设置环境变量 VITE_LOG_CLEAR=1
export async function clearAllLogs(): Promise<boolean> {
    const enabled = import.meta.env.VITE_LOG_CLEAR === "1";
    if (!enabled) return false;
    try {
        await http.post("/app/logs/clear");
        return true;
    } catch {
        return false;
    }
}
