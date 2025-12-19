import { ApiClient } from "@/services";
import Cookies from "js-cookie";
import { useAuthStore } from "@/store";

const getBaseUrl = () => "/api/v1";

let clientInstance: ApiClient | null = null;

export function getClientApi() {
  if (clientInstance) return clientInstance;

  clientInstance = new ApiClient(
    { baseURL: getBaseUrl() },
    () => {
      // 优先从 Store 读，Store 没有则读 Cookie
      return useAuthStore.getState().accessToken || Cookies.get("access_token") || null;
    },
    () => {
      useAuthStore.getState().logout();
      if (typeof window !== "undefined") {
        window.location.href = "/auth/login";
      }
    }
  );

  return clientInstance;
}
