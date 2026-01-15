import { ApiClient } from "@/services";
import Cookies from "js-cookie";
import { useAuthStore } from "@/store";
import { getOrSetVisitorId } from "../utils";

const getBaseUrl = () => "/api/v1";

// Get the base path from Next.js configuration
const getBasePath = () => {
  if (typeof window !== "undefined") {
    // Extract base path from the script src or pathname
    const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";
    return basePath;
  }
  return "";
};

let clientInstance: ApiClient | null = null;
let cachedToken: string | null = null;
let cachedVisitorId: string | null = null;

export function getClientApi() {
  const state = useAuthStore.getState();
  const token = state.accessToken || Cookies.get("access_token") || null;
  let visitorId = state.visitorId || Cookies.get("visitor_id") || null;
  if (!token && !visitorId) {
    visitorId = getOrSetVisitorId();
  }

  if (
    !clientInstance ||
    token !== cachedToken ||
    visitorId !== cachedVisitorId
  ) {
    cachedToken = token;
    cachedVisitorId = visitorId;

    clientInstance = new ApiClient(
      { baseURL: getBaseUrl() },
      token,
      visitorId,
      () => {
        useAuthStore.getState().logout();
        if (typeof window !== "undefined") {
          const basePath = getBasePath();
          const loginPath = `${basePath}/auth/login`;
          if (!window.location.pathname.startsWith(loginPath)) {
            const currentPath = encodeURIComponent(
              window.location.pathname + window.location.search,
            );
            window.location.href = `${loginPath}?redirect=${currentPath}`;
          }
        }
      },
    );
  }

  return clientInstance;
}
