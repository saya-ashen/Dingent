import type { AxiosInstance } from "axios";
import { PluginManifest } from "../types";

export function createPluginsApi(http: AxiosInstance, pluginsBase: string) {
  const url = (p = "") => `${pluginsBase}${p}`;

  return {
    async getAvailablePlugins(): Promise<PluginManifest[] | null> {
      const { data } = await http.get<PluginManifest[]>(url("/"));
      return data;
    },

    async deletePlugin(pluginId: string): Promise<void> {
      await http.delete(url(`/${pluginId}`));
    }
  };
}


