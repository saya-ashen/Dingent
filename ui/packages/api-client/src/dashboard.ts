import type { AxiosInstance } from "axios";
import { extractErrorMessage } from "./http";
import type {
  AppSettings,
  Assistant,
  OverviewData,
  AnalyticsData,
} from "./types/index.js";

/**
 * Creates a dashboard-specific API client.
 * @param http The Axios instance to use for requests.
 * @returns An object with dashboard-specific methods.
 */
export function createDashboardApi(http: AxiosInstance) {
  return {
    getOverview: async (): Promise<OverviewData> => {
      try {
        const { data } = await http.get<OverviewData>("/overview");
        return data;
      } catch (err) {
        throw new Error(`Failed to fetch overview: ${extractErrorMessage(err)}`);
      }
    },

    getBudget: async (): Promise<AnalyticsData> => {
      try {
        const { data } = await http.get<AnalyticsData>("/overview/budget");
        return data;
      } catch (err) {
        throw new Error(`Failed to fetch budget: ${extractErrorMessage(err)}`);
      }
    },

    getAppSettings: async (): Promise<AppSettings | null> => {
      try {
        const { data } = await http.get<AppSettings>("/settings");
        return data;
      } catch (err) {
        throw new Error(`Failed to fetch app settings: ${extractErrorMessage(err)}`);
      }
    },
    saveAppSettings: async (payload: AppSettings): Promise<void> => {
      try {
        // Use PATCH for partial updates
        await http.patch("/settings", payload);
      } catch (err) {
        throw new Error(`Failed to save app settings: ${extractErrorMessage(err)}`);
      }
    },
    getAssistantsConfig: async (): Promise<Assistant[] | null> => {
      try {
        const { data } = await http.get<Assistant[]>("/assistants");
        return data;
      } catch (err) {
        return [];
      }
    },



    // ... and so on for all other functions from your original file
  };
}
