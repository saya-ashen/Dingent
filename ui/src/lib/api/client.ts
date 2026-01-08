import { ApiClient } from "@/services";
import Cookies from "js-cookie";
import { useAuthStore } from "@/store";
import { getOrSetVisitorId } from "../utils";

const getBaseUrl = () => "/api/v1";

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
          if (!window.location.pathname.startsWith("/auth/login")) {
            const currentPath = encodeURIComponent(
              window.location.pathname + window.location.search,
            );
            window.location.href = `/auth/login?redirect=${currentPath}`;
          }
        }
      },
    );
  }

  return clientInstance;
}
