import type { AxiosInstance } from "axios";
import type { AppSettings } from "../types";

export function createSettingsApi(http: AxiosInstance, agentSettingsBase: string) {
  const url = (p = "") => `${agentSettingsBase}${p}`;

  return {

    async getAppSettings(): Promise<AppSettings | null> {
      const { data } = await http.get<AppSettings>(url("/"));
      return data;
    },

    async saveAppSettings(payload: AppSettings): Promise<void> {
      await http.patch(url("/"), payload);
    },
  };
}




