import axios, { AxiosError } from "axios";

export class ApiError extends Error {
  status?: number;
  details?: unknown;

  constructor(message: string, status?: number, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

/** Normalize axios (and non-axios) errors into user-friendly ApiError */
export function toApiError(err: unknown): ApiError {
  if (axios.isAxiosError(err)) {
    const ax = err as AxiosError<any>;
    const status = ax.response?.status;
    const data = ax.response?.data;

    // common FastAPI-style error surface: {"detail": "..."}
    const detail =
      data && typeof data === "object" && "detail" in data ? String(data.detail) :
        typeof data === "string" ? data :
          status ? `Request failed with status code ${status}` :
            ax.message || "A network error occurred";

    return new ApiError(detail, status ?? undefined, data);
  }
  return new ApiError(String(err));
}
