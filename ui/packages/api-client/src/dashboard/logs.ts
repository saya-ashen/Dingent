import type { AxiosInstance } from "axios";
import type { LogItem, LogStats } from "../types";

export function createLogsApi(http: AxiosInstance, logsBase: string) {
  const url = (p = "") => `${logsBase}${p}`;

  return {
    async getLogs(params: { level?: string | null; module?: string | null; limit?: number | null; search?: string | null; }): Promise<LogItem[]> {
      const { data } = await http.get<LogItem[]>(url(""), { params });
      return data;
    },

    async getStats(): Promise<LogStats> {
      try {
        const { data } = await http.get<LogStats>(url("/stats"));
        return data;
      } catch {
        return { total_logs: 0, by_level: {}, by_module: {}, oldest_timestamp: null, newest_timestamp: null };
      }
    },

    async clearAll(): Promise<boolean> {
      try {
        // If your backend prefers DELETE /logs, change here
        await http.delete(url("/clear"));
        return true;
      } catch {
        return false;
      }
    },
  };
}

