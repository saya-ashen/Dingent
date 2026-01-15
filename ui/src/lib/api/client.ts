import { ApiClient } from "@/services";
import Cookies from "js-cookie";
import { useAuthStore } from "@/store";
import { getOrSetVisitorId } from "../utils";

const getBaseUrl = () => "/api/v1";

// Get the base path from the current URL pathname
// This extracts the base path by checking if the pathname contains known routes
const getBasePath = () => {
  if (typeof window !== "undefined") {
    const pathname = window.location.pathname;
    // Check if pathname starts with a base path by looking for common routes
    // e.g., "/dingent/web/auth/login" -> "/dingent/web"
    const knownRoutes = ["/auth/", "/guest/", "/api/"];
    for (const route of knownRoutes) {
      const index = pathname.indexOf(route);
      if (index > 0) {
        return pathname.substring(0, index);
      }
    }
    // If at root or unknown route, check for base path in script sources
    const scripts = document.getElementsByTagName("script");
    for (const script of scripts) {
      const src = script.getAttribute("src");
      if (src && src.includes("/_next/")) {
        const match = src.match(/^(\/[^/]+)?(\/_next\/)/);
        if (match && match[1]) {
          return match[1];
        }
      }
    }
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
