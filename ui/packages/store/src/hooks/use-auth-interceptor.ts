"use client";
import { useEffect, useRef } from "react";
import { usePathname, useRouter } from "next/navigation";

const LOGIN_PATH = "/auth/login";
// You can make this configurable if different apps have different endpoints
const AUTH_GUARDED_ENDPOINTS = ["/api/copilotkit", "/api/v1/frontend/", "/api/v1/dashboard/"];

export function useAuthInterceptor() {
  const pathname = usePathname();
  const router = useRouter();
  const redirectingRef = useRef(false);

  useEffect(() => {
    // Don't patch on the login page to avoid redirect loops
    if (pathname.startsWith(LOGIN_PATH)) return;

    const originalFetch = window.fetch;

    const toUrl = (input: RequestInfo | URL): string => {
      if (typeof input === "string") return input;
      if (input instanceof URL) return input.toString();
      return input?.url?.toString?.() ?? "";
    };

    const shouldIntercept = (url: string): boolean => {
      try {
        const u = new URL(url, window.location.origin);
        return AUTH_GUARDED_ENDPOINTS.some(ep => u.pathname.startsWith(ep));
      } catch {
        return false;
      }
    };

    window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const res = await originalFetch(input, init);

      if (!redirectingRef.current && res.status === 401 && shouldIntercept(toUrl(input))) {
        redirectingRef.current = true;
        const next = encodeURIComponent(window.location.pathname + window.location.search);
        router.replace(`${LOGIN_PATH}?next=${next}`);
        // Throw an error to prevent the original caller from processing the 401 response
        throw new Error("Unauthorized: Redirecting to login.");
      }

      return res;
    };

    // Cleanup function to restore the original fetch
    return () => {
      window.fetch = originalFetch;
      redirectingRef.current = false;
    };
  }, [pathname, router]);
}
