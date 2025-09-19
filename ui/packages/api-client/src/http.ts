import axios, { type AxiosInstance } from "axios";

const HTTP_TIMEOUT = 120_000;

/**
 * Creates a configured Axios instance.
 * @param baseURL The base URL for the API endpoints.
 * @param tokenKey The key for the auth token in localStorage.
 * @returns A configured Axios instance.
 */
export function createHttpInstance(baseURL: string, tokenKey: string): AxiosInstance {
  const instance = axios.create({
    baseURL,
    timeout: HTTP_TIMEOUT,
  });

  // Add a request interceptor to include the auth token
  instance.interceptors.request.use((config) => {
    // Check if window is defined to prevent server-side errors
    if (typeof window !== "undefined") {
      const token = localStorage.getItem(tokenKey);
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  });

  return instance;
}

/**
 * Extracts a user-friendly error message from an API error.
 * @param err The error object.
 * @returns A string containing the error message.
 */
export function extractErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const resp = err.response;
    if (resp?.data && typeof resp.data === "object" && "detail" in resp.data) {
      return String((resp.data as any).detail);
    }
    if (typeof resp?.data === "string") return resp.data;
    if (resp?.status) return `Request failed with status code ${resp.status}`;
    return err.message || "A network error occurred";
  }
  return String(err);
}
