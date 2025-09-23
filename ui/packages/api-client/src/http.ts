import axios, { type AxiosInstance, isAxiosError } from "axios";
import type { ApiClientConfig } from "./config";
import { useAuthStore } from "@repo/store";
import { toApiError } from "./errors";

let isRedirecting = false;

export function createHttp(config: ApiClientConfig): AxiosInstance {
  const instance = axios.create({
    baseURL: config.baseURL,
    timeout: config.timeoutMs ?? 120_000,
  });

  instance.interceptors.request.use((config) => {
    const token = useAuthStore.getState().accessToken;
    console.log("tokenxxxxx", token)
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  instance.interceptors.response.use(
    // On success, just return the response
    (resp) => resp,
    // On error, check for 401 status
    (err) => {
      // Check if it's an Axios error and has a 401 status code
      if (isAxiosError(err) && err.response?.status === 401) {

        // This logic should only run on the client side.
        // The !isRedirecting flag prevents a redirect loop if multiple API calls fail.
        if (typeof window !== "undefined" && !isRedirecting) {
          isRedirecting = true;

          // You might have a 'reset' or 'logout' function in your store
          // It's good practice to clear the invalid token and user state.
          const resetAuthState = useAuthStore.getState().reset;
          if (resetAuthState) {
            resetAuthState();
          }

          // For better user experience, redirect the user back to the page
          // they were on after they successfully log in.
          const next = encodeURIComponent(window.location.pathname + window.location.search);
          const loginUrl = `/auth/login?next=${next}`;

          // Perform the redirect
          window.location.href = loginUrl;

          // Return a new promise that never resolves to prevent the original
          // promise chain from continuing (e.g., hitting a .catch() block in the UI)
          return new Promise(() => { });
        }
      }

      // For any other error, pass it through the original error handler.
      return Promise.reject(toApiError(err));
    }
  );

  return instance;
}
