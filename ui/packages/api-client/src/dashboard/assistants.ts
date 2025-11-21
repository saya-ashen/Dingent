import type { AxiosInstance } from "axios";

import type { Assistant, } from "../types";
export function createAssistantsApi(http: AxiosInstance, assistantsBase: string) {
  const url = (p = "") => `${assistantsBase}${p}`;

  return {
    async getAssistantsConfig(): Promise<Assistant[]> {
      try {
        const { data } = await http.get<Assistant[]>(url("/"));
        return data;
      } catch {
        return [];
      }
    },

    async addAssistant(name: string, description: string): Promise<Assistant> {
      const { data } = await http.post<Assistant>(url("/"), { name, description });
      return data;
    },

    async deleteAssistant(assistantId: string): Promise<void> {
      await http.delete(url(`/${assistantId}`));
    },

    async addPluginToAssistant(assistantId: string, pluginId: string): Promise<void> {
      await http.post(url(`/${assistantId}/plugins`), { registry_id: pluginId });
    },

    async removePluginFromAssistant(assistantId: string, registry_id: string): Promise<void> {
      await http.delete(url(`/${assistantId}/plugins/${registry_id}`));
    },

    async updateAssistant(assistantId: string, payload: Partial<Assistant>): Promise<Assistant> {
      // normalize plugin.config array → object
      const transformed = structuredClone(payload);
      transformed.plugins?.forEach((plugin: any) => {
        if (Array.isArray(plugin?.config)) {
          const obj = (plugin.config as any[]).reduce((acc, item: any) => {
            if (item?.name && item?.value !== undefined && item?.value !== null) {
              acc[item.name] = item.value;
            }
            return acc;
          }, {} as Record<string, unknown>);
          plugin.config = obj;
        }
      });

      const { data } = await http.patch(url(`/${assistantId}`), transformed);
      return data;
    },

  };
}


